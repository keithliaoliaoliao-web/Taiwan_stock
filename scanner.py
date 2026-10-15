# ==============================================================================
# scanner.py
# 臺股價格行為 H2 突破 ＋ 投信買超濾網 C — GitHub Actions 盤中/盤後自動掃描器
# ==============================================================================
import os, sys, time, requests
from datetime import datetime
import numpy as np, pandas as pd, yfinance as yf
from price_action_engine import PriceActionEngine
from taiwan_market_rules import next_tick_price, previous_tick_price

TOTAL_CAPITAL = 1_000_000.0
MAX_POSITIONS = 3
ALLOCATION_PER_TRADE = TOTAL_CAPITAL / MAX_POSITIONS
PORTFOLIO_FILE = "portfolio.csv"
OUTPUT_HTML = "index.html"

# 1. 讀取持倉記錄
if os.path.exists(PORTFOLIO_FILE):
    portfolio_df = pd.read_csv(PORTFOLIO_FILE)
    holding_trades = portfolio_df[portfolio_df["status"] == "HOLDING"].copy()
else:
    holding_trades = pd.DataFrame()

# 2. 讀取 150 檔成分股
wl_df = pd.read_csv("watchlist.csv")
ticker_name_map = dict(zip(wl_df["ticker"], wl_df["name"]))
universe = wl_df["ticker"].tolist()

HEADERS = {"User-Agent": "Mozilla/5.0"}
dfs = {}

def fetch_latest_bars(ticker: str) -> pd.DataFrame:
    clean_sym = ticker.split(".")[0].strip()
    candidates = [f"{clean_sym}.TW", f"{clean_sym}.TWO"] if not ticker.startswith("^") else [ticker]
    for sym in candidates:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1y"
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            if r.status_code == 200:
                res = r.json().get("chart", {}).get("result", [])
                if res:
                    ts = res[0].get("timestamp", [])
                    quote = res[0].get("indicators", {}).get("quote", [{}])[0]
                    rows = []
                    for i in range(len(ts)):
                        o, h, l, c = quote.get("open", [])[i], quote.get("high", [])[i], quote.get("low", [])[i], quote.get("close", [])[i]
                        v = quote.get("volume", [])[i] if quote.get("volume") else 0
                        if None in (o, h, l, c) or pd.isna(o): continue
                        dt = datetime.fromtimestamp(ts[i]).strftime("%Y-%m-%d")
                        rows.append({"Date": dt, "Open": float(o), "High": float(h), "Low": float(l), "Close": float(c), "Volume": int(v or 0)})
                    if len(rows) >= 120:
                        return pd.DataFrame(rows).drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)
        except Exception:
            continue
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if not df.empty and len(df) >= 120:
            df = df.reset_index()
            df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
            return df[["Date", "Open", "High", "Low", "Close", "Volume"]].dropna().reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame()

print(">>> 正在同步 150 檔日線行情...")
for i, tkr in enumerate(universe, 1):
    df_t = fetch_latest_bars(tkr)
    if not df_t.empty: dfs[tkr] = df_t

# 3. 監控個人真實持倉
holding_rows_html = ""
total_market_val = 0.0
total_unrealized_pnl = 0.0
any_exit_alert = False

if not holding_trades.empty:
    for _, row in holding_trades.iterrows():
        tkr = str(row["ticker"])
        name = row.get("name", ticker_name_map.get(tkr, tkr))
        shares = int(row["shares"])
        entry_p = float(row["entry_price"])
        df_h = dfs.get(tkr)
        if df_h is not None and not df_h.empty:
            df_ind = PriceActionEngine._prepare_indicators(df_h)
            last_b = df_ind.iloc[-1]
            cur_p = float(last_b["Close"])
            ema_20 = float(last_b["EMA_20"])
            is_broken = bool(cur_p < ema_20)
            mkt_val = cur_p * shares
            pnl = (cur_p - entry_p) * shares
            ret_pct = ((cur_p - entry_p) / entry_p) * 100.0
            total_market_val += mkt_val
            total_unrealized_pnl += pnl
            if is_broken:
                any_exit_alert = True
                badge = '<span class="badge bg-danger" style="padding:6px 10px;">🔴 跌破 20EMA（次日開盤市價全數賣出）</span>'
            else:
                badge = '<span class="badge bg-success" style="padding:6px 10px;">🟢 持穩 20EMA（繼續持有）</span>'
            color = "#dc3545" if pnl < 0 else "#198754"
            holding_rows_html += f"""
            <tr>
                <td><strong>{tkr}</strong></td><td>{name}</td><td>{row['entry_date']}</td><td>{shares:,}</td>
                <td>{entry_p:.2f}</td><td><strong>{cur_p:.2f}</strong></td><td>{ema_20:.2f}</td>
                <td style="color:{color}; font-weight:bold;">{pnl:+,.0f} 元 ({ret_pct:+.2f}%)</td><td>{badge}</td>
            </tr>"""

# 4. 掃描明日 H2 突破 ＋ 投信買超訊號
h2_candidates = []
for tkr, df in dfs.items():
    if len(df) < 120: continue
    df_analyzed = PriceActionEngine.analyze_setups(df)
    last_r = df_analyzed.iloc[-1]
    if last_r.get("Signal_H2") == True:
        h2_candidates.append({
            "ticker": tkr, "name": ticker_name_map.get(tkr, tkr),
            "date": str(last_r["Date"]), "grade": str(last_r["Signal_Grade"]),
            "close_price": float(last_r["Close"]), "trigger_price": float(last_r["Trigger_Price"]),
            "stop_loss": float(last_r["Stop_Loss"]), "target_price": float(last_r["Target_Price"])
        })

signals_rows_html = ""
CHIP_API_URL = "https://api.finmindtrade.com/api/v4/data"
new_signals_count = 0

for item in h2_candidates:
    sid = item["ticker"].split(".")[0]
    sig_dt = item["date"]
    start_dt = (pd.to_datetime(sig_dt) - pd.Timedelta(days=15)).strftime("%Y-%m-%d")
    t_net, t_5d = 0, 0
    try:
        r = requests.get(CHIP_API_URL, params={"dataset": "TaiwanStockInstitutionalInvestorsBuySell", "data_id": sid, "start_date": start_dt, "end_date": sig_dt}, headers=HEADERS, timeout=6)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                df_c = pd.DataFrame(data)
                df_c["net"] = df_c["buy"] - df_c["sell"]
                day_c = df_c[df_c["date"] == sig_dt]
                t_rows = day_c[day_c["name"].str.contains("Investment_Trust", case=False, na=False)]
                if not t_rows.empty: t_net = t_rows["net"].sum()
                trust_all = df_c[df_c["name"].str.contains("Investment_Trust", case=False, na=False)]
                if not trust_all.empty: t_5d = trust_all.tail(5)["net"].sum()
    except Exception:
        pass
    if (t_net > 0 or t_5d > 0):
        new_signals_count += 1
        ep = item["trigger_price"]
        s_shares = max(1000, int((ALLOCATION_PER_TRADE / ep) // 1000 * 1000)) if ep > 0 else 0
        signals_rows_html += f"""
        <tr>
            <td><strong>{item['ticker']}</strong></td><td>{item['name']}</td>
            <td><span class="badge bg-primary">{item['grade']} 級</span></td>
            <td>{item['close_price']:.2f}</td><td style="color:#0d6efd; font-weight:bold;">{ep:.2f}</td>
            <td style="color:#dc3545;">{item['stop_loss']:.2f}</td><td style="color:#198754;">{item['target_price']:.2f}</td>
            <td>{int(t_net/1000):+d} 張 (5日: {int(t_5d/1000):+d} 張)</td><td><strong>{s_shares:,} 股</strong></td>
            <td>{int(s_shares * ep):,} 元</td>
        </tr>"""

status_bg = "#dc3545" if any_exit_alert else ("#198754" if new_signals_count > 0 else "#6c757d")
status_title = "🔴 賣出警示" if any_exit_alert else ("🟢 買進訊號" if new_signals_count > 0 else "⚪ 續抱 / 空手觀望")
status_desc = "持倉中有標的收盤跌破 20EMA，請於明日開盤市價賣出！" if any_exit_alert else (f"偵測到 {new_signals_count} 檔 H2 突破＋投信買超標的！" if new_signals_count > 0 else "持倉狀態健康，今日無新進場標的。")

# 5. 生成完整 HTML 檔案
html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8"><title>臺股價格行為量化儀表板</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f8f9fa; font-family: -apple-system, sans-serif; }}
        .card {{ border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: none; }}
        .header-box {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; }}
        .light-box {{ background-color: {status_bg}; color: white; padding: 16px 20px; border-radius: 12px; font-weight: bold; margin-bottom: 20px; }}
    </style>
</head>
<body>
<div class="container py-4">
    <div class="header-box d-flex justify-content-between align-items-center">
        <div><h3 class="mb-1">📊 臺股價格行為選股系統（Al Brooks H2 ＋ 投信濾網）</h3><small>V1 20EMA 趨勢追蹤體系</small></div>
        <span class="badge bg-light text-dark">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
    </div>
    <div class="light-box"><h4>{status_title}</h4><div>{status_desc}</div></div>
    
    <div class="row g-3 mb-3">
        <div class="col-md-3"><div class="card p-3 text-center"><div class="text-muted">總預算規模</div><h4>{TOTAL_CAPITAL:,.0f} 元</h4></div></div>
        <div class="col-md-3"><div class="card p-3 text-center"><div class="text-muted">持股市值</div><h4>{total_market_val:,.0f} 元</h4></div></div>
        <div class="col-md-3"><div class="card p-3 text-center"><div class="text-muted">未實現損益</div><h4 style="color:{'#dc3545' if total_unrealized_pnl < 0 else '#198754'};">{total_unrealized_pnl:+,.0f} 元</h4></div></div>
        <div class="col-md-3"><div class="card p-3 text-center"><div class="text-muted">持倉檔數</div><h4>{len(holding_trades)} / {MAX_POSITIONS} 檔</h4></div></div>
    </div>

    <div class="card p-4">
        <h5 class="text-primary mb-3">🎯 明日掛單進場清單（H2 突破 ＋ 投信買超）</h5>
        <div class="table-responsive"><table class="table table-hover align-middle">
            <thead class="table-light"><tr><th>代號</th><th>名稱</th><th>評級</th><th>今日收盤</th><th>掛單進場價</th><th>停損價</th><th>目標價</th><th>投信籌碼</th><th>建議股數</th><th>預估金額</th></tr></thead>
            <tbody>{signals_rows_html if signals_rows_html else '<tr><td colspan="10" class="text-center py-3 text-muted">今日無符合條件之新訊號</td></tr>'}</tbody>
        </table></div>
    </div>

    <div class="card p-4">
        <h5 class="text-success mb-3">📈 個人持倉 20EMA 監控帳本</h5>
        <div class="table-responsive"><table class="table table-hover align-middle">
            <thead class="table-light"><tr><th>代號</th><th>名稱</th><th>買進日期</th><th>持有股數</th><th>成本均價</th><th>今日收盤</th><th>20EMA</th><th>浮動損益</th><th>操作指示</th></tr></thead>
            <tbody>{holding_rows_html if holding_rows_html else '<tr><td colspan="9" class="text-center py-3 text-muted">目前 portfolio.csv 中無持倉記錄</td></tr>'}</tbody>
        </table></div>
    </div>
</div>
</body>
</html>"""

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ {OUTPUT_HTML} 已成功更新！")

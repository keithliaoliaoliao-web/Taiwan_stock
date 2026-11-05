# Taiwan Stock Price Action Dashboard

公開的台股技術掃描儀表板 ＋ Price Action 策略原始碼（Brooks H1/H2、MTR、Wedge、BOM、Climax）。

## 架構

```
daily_scan.yml       ← GitHub Actions 每個交易日自動掃描（掃描後 commit scan_result.json）
freeze_rerun.yml     ← 手動觸發：BOM／H2／MTR／Wedge 分段凍結重跑，上傳 artifact
index.html           ← GitHub Pages 靜態儀表板
price_action_scanner.py / price_action_engine.py / backtest.py
                     ← 掃描／分析／回測引擎
watchlist.csv        ← 觀察池（150 檔，公開市場資料）
```

## 隱私說明

- 本 repo 不包含 `holdings.json`、紙上交易帳本或任何個人持股資訊
- 前端持倉只存在瀏覽器 `localStorage`
- `scan_result.json` 的 `holdings_status` 固定為空陣列（`[]`）

## 策略聲明

本 repo 公開策略原始碼供研究交流。**所有績效數字僅供參考：未經樣本外驗證、非投資建議。** 策略結果受市場環境、滑價、流動性、除權息等因素影響，未來表現無法保證。

## 降級聲明（必讀，2026-11-05 更新）

- 凍結證據（final4, +0.55R）**不可再引用**——那是因 BOM ATR 來源錯誤（簡單 High-Low 平均 → 過濾了最賺錢的 AI 行情信號）造成的虛高
- 修正後 BOM（V1 出場）：PF 1.21、**扣除最賺 5 筆後期望值 ≈ +0.04R**
- SHORT 策略全面虧損，已停用
- LONG-only 期望值約 +0.71R，但高度依賴 2024–2026 台股 AI 超級行情的右尾大赢家，**無法複製，不是 edge**
- 此為學習／研究專案，**不建議且不可用於實盤或任何可獲利宣稱**

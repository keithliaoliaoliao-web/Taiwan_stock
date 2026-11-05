# Taiwan Stock Price Action Dashboard

公開的台股技術掃描儀表板：

- 每日自動執行 Price Action 掃描器（Brooks H1/H2、MTR、Wedge、BOM、Climax）
- 儀表板顯示掃描結果（`scan_result.json`）
- 持倉功能為純前端 `localStorage`，本 repo 不存放任何個人資料

## 架構

```
daily_scan.yml   ← GitHub Actions 每日排程（scan 全部股票池並 commit scan_result.json）
index.html       ← GitHub Pages 靜態儀表板
price_action_scanner.py / price_action_engine.py / data_fetcher.py
                 ← 掃描引擎
watchlist.csv    ← 觀察池（150 檔，公開市場資料）
```

## 隱私說明

- 本 repo 不包含 `holdings.json`、紙上交易帳本或任何個人持股資訊
- 前端持倉只存在瀏覽器 `localStorage`
- `scan_result.json` 的 `holdings_status` 固定為空陣列（`[]`）

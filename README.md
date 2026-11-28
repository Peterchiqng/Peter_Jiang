# 投資儀表板

四個頁面：每日股市（daily.html）、S&P 500 預估估值（index.html）、台股大盤本益比（taiex.html）、個股儀表板（stock.html）。

## 每日自動更新
- `.github/workflows/market.yml`：台灣時間週一至週五 06:10 執行 `scripts/market_crawl.py`，更新 `market/data/market.json`（台股大盤本益比來自證交所月報，指數價格來自 Yahoo Finance，預估 EPS 來自 FactSet 共識）。台股大盤頁直接讀這個檔案。
- `.github/workflows/update-data.yml`：週一至週五 18:30 更新 `data/` 內的個股資料（FinMind，不需 token）。

第一次請到 Actions 分頁手動執行「大盤估值資料更新」與「update-data」各一次。

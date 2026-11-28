# 投資儀表板網站（三個獨立頁面）

| 檔案 | 內容 |
|---|---|
| index.html | S&P 500 預估估值儀表板 |
| taiex.html | 台股大盤本益比河流圖 + 標準差分析 |
| stock.html | 個股投資儀表板（含 FactSet 預估區塊） |
| tickers.json | 每日自動更新的股票代號清單 |
| fetch_data.py | 抓取 FinMind 資料，產生 data/*.json |
| .github/workflows/update-data.yml | GitHub Actions 排程（台灣時間週一至五 18:30） |
| nav-snippet.html | 若保留自己較新的個股頁，貼上這段即可加入共用導覽列 |

## ⚠ 部署前先看
你的 GitHub Pages 儲存庫若已有 `index.html`（例如原本的個股儀表板），上傳這包的 `index.html` 會**覆蓋它**。
請先：
1. 把原本的 `index.html` 下載備份。
2. 若原本那份比這包的 `stock.html` 新（例如有持股分頁），把它改名為 `stock.html` 上傳，覆蓋這包的版本，再把 `nav-snippet.html` 的內容貼到它的 `<body>` 開頭。

## 部署步驟（不需寫程式）
1. 開啟 GitHub 儲存庫 → Add file → Upload files，把整包檔案（含 `.github` 資料夾）拖進去 → Commit。
2. Settings → Pages → Source 選 `main` / root。
3. Actions 分頁 → update-data → Run workflow，跑完後會產生 `data/` 資料夾，個股頁就有每日更新資料。
4. （選填）Settings → Secrets → 新增 `FINMIND_TOKEN` 可提高請求上限；沒有也能運作。

## 新增個股
編輯 `tickers.json` 加入代號，再手動執行一次 Actions。FactSet 預估可編輯 `data/factset.json` 擴充。

## 資料提醒
- S&P 500 與台股大盤頁的「最新值」為 2026/05 快照，請依需要更新。
- 台股 1986–2020 年度本益比與部分 S&P 歷史年底值為彙整近似值，引用前請核對官方資料。
- 本站僅供資訊整理，不構成投資建議。

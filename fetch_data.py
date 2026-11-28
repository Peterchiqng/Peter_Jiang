#!/usr/bin/env python3
"""每日抓取 FinMind 開放資料，輸出 data/代號.json 與 data/index.json。
不需要 token（有設定 FINMIND_TOKEN 環境變數時會自動使用，可提高請求上限）。"""
import json, os, time, datetime as dt, urllib.parse, urllib.request

API = "https://api.finmindtrade.com/api/v4/data"
TOKEN = os.environ.get("FINMIND_TOKEN", "").strip()
OUT = "data"
os.makedirs(OUT, exist_ok=True)
today = dt.date.today()

def get(dataset, **kw):
    q = {"dataset": dataset, **kw}
    if TOKEN:
        q["token"] = TOKEN
    url = API + "?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8"))
    return d.get("data", [])

def safe(dataset, **kw):
    for _ in range(2):
        try:
            return get(dataset, **kw)
        except Exception as e:
            print("  !", dataset, e)
            time.sleep(3)
    return []

def ago(days):
    return (today - dt.timedelta(days=days)).isoformat()

tickers = json.load(open("tickers.json", encoding="utf-8"))
names = {}
info = safe("TaiwanStockInfo")
for r in info:
    if r.get("stock_id") and r.get("stock_name"):
        names.setdefault(r["stock_id"], r["stock_name"])

index = []
for t in tickers:
    print("fetch", t)
    price = safe("TaiwanStockPrice", data_id=t, start_date=ago(365 * 10))
    if not price:
        print("  skip (no price)")
        continue
    obj = {
        "updated": today.isoformat(),
        "price": price,
        "per": safe("TaiwanStockPER", data_id=t, start_date=ago(25)),
        "fin": safe("TaiwanStockFinancialStatements", data_id=t, start_date=ago(365 * 12)),
        "rev": safe("TaiwanStockMonthRevenue", data_id=t, start_date=ago(365 * 11)),
    }
    with open(f"{OUT}/{t}.json", "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    index.append({"id": t, "name": names.get(t, t)})
    time.sleep(1)

if index:
    with open(f"{OUT}/index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
print("done", len(index))

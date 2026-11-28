"""S&P 500 官方盈餘資料：S&P Dow Jones Indices「sp-500-eps-est.xlsx」。

提供季度營業 EPS（operating）與 As Reported EPS 的實際值與預估。
輸出 market/data/spx_eps.json：
  q      每季 [{d, op, rep, est}]（est=True 代表預估）
  ttm    近四季加總 [{d, op, rep, est}]
  annual 每個日曆年加總 {年: {op, rep, est}}
  debug  解析過程（工作表名稱、表頭位置、前幾列），檔案格式改版時用來排查

檔案版面無法在撰寫時確認，因此解析採用「找表頭＋找日期欄」的寬鬆方式，
解析失敗時不會覆蓋舊資料，只會把原因寫進 debug。
需要 openpyxl（GitHub Actions 內 pip install openpyxl）。
"""
import datetime as dt
import io
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "market", "data", "spx_eps.json")
URLS = [
    "https://www.spglobal.com/spdji/en/documents/additional-material/sp-500-eps-est.xlsx",
    "https://www.spglobal.com/spdji/en/documents/additional-material/sp-500-eps-est.xlsx?download=true",
]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
TODAY = dt.date.today()


def download():
    last = None
    for u in URLS:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "*/*", "Referer": "https://www.spglobal.com/spdji/en/indices/equity/sp-500/"})
            with urllib.request.urlopen(req, timeout=60) as r:
                b = r.read()
            if b[:2] == b"PK":
                return b
            last = f"不是 xlsx（開頭 {b[:20]!r}）"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
    raise RuntimeError("下載失敗：" + str(last))


def as_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, str):
        s = v.strip()
        for f in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%d-%b-%Y", "%b %d, %Y"):
            try:
                return dt.datetime.strptime(s, f).date()
            except ValueError:
                pass
    return None


def as_num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.replace(",", "").replace("$", "").strip()
        try:
            return float(s)
        except ValueError:
            return None
    return None


def find_columns(rows):
    """回傳 (表頭列索引, 日期欄, 營業EPS欄, 報告EPS欄)；找不到回 None。"""
    for i, row in enumerate(rows[:60]):
        txt = [str(c).lower() if c is not None else "" for c in row]
        op = [j for j, t in enumerate(txt) if "operating" in t and "p/e" not in t and "pe" not in t.split()]
        rep = [j for j, t in enumerate(txt) if ("as reported" in t or "reported" in t) and "p/e" not in t]
        if op and rep:
            # 日期欄：表頭下方第一個含日期值的欄
            for j in range(min(len(row), 6)):
                n = 0
                for r in rows[i + 1:i + 40]:
                    if j < len(r) and as_date(r[j]):
                        n += 1
                if n >= 5:
                    return i, j, op[0], rep[0]
    return None


def parse(xbytes):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(xbytes), data_only=True, read_only=True)
    debug = {"sheets": wb.sheetnames, "tried": []}
    best = []
    for name in wb.sheetnames:
        rows = [list(r) for r in wb[name].iter_rows(values_only=True)]
        found = find_columns(rows)
        debug["tried"].append({"sheet": name, "rows": len(rows), "found": bool(found), "head": [[str(c)[:18] if c is not None else "" for c in r[:8]] for r in rows[:6]]})
        if not found:
            continue
        i, jd, jo, jr = found
        out = []
        for r in rows[i + 1:]:
            d = as_date(r[jd]) if jd < len(r) else None
            op = as_num(r[jo]) if jo < len(r) else None
            rep = as_num(r[jr]) if jr < len(r) else None
            if d and (op is not None or rep is not None):
                out.append({"d": d.isoformat(), "op": op, "rep": rep})
        if len(out) > len(best):
            best = out
            debug["used"] = {"sheet": name, "header_row": i, "cols": [jd, jo, jr]}
    return best, debug


def build(rows):
    seen = {}
    for r in rows:
        seen[r["d"]] = r  # 同一天後者優先
    q = []
    for d in sorted(seen):
        r = seen[d]
        dd = dt.date.fromisoformat(d)
        # 季末日；季末後 30 天內尚未公布 → 視為預估
        est = (TODAY - dd).days < 30
        q.append({"d": d, "op": r["op"], "rep": r["rep"], "est": est})
    ttm = []
    for i in range(3, len(q)):
        w = q[i - 3:i + 1]
        # 確認是連續四季（間隔約 3 個月）
        gaps = [(dt.date.fromisoformat(w[k + 1]["d"]) - dt.date.fromisoformat(w[k]["d"])).days for k in range(3)]
        if not all(80 <= g <= 100 for g in gaps):
            continue
        ttm.append({"d": w[-1]["d"],
                    "op": round(sum(x["op"] for x in w), 2) if all(x["op"] is not None for x in w) else None,
                    "rep": round(sum(x["rep"] for x in w), 2) if all(x["rep"] is not None for x in w) else None,
                    "est": any(x["est"] for x in w)})
    annual = {}
    for x in q:
        y = x["d"][:4]
        a = annual.setdefault(y, {"op": 0.0, "rep": 0.0, "n": 0, "est": False, "_o": True, "_r": True})
        a["n"] += 1
        a["est"] = a["est"] or x["est"]
        if x["op"] is None: a["_o"] = False
        else: a["op"] += x["op"]
        if x["rep"] is None: a["_r"] = False
        else: a["rep"] += x["rep"]
    ann = {y: {"op": round(a["op"], 2) if a["_o"] else None, "rep": round(a["rep"], 2) if a["_r"] else None, "est": a["est"]}
           for y, a in annual.items() if a["n"] == 4}
    return q, ttm, ann


def main():
    prev = {}
    if os.path.exists(OUT):
        prev = json.load(open(OUT, encoding="utf-8"))
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    try:
        rows, debug = parse(download())
        if len(rows) < 20:
            raise RuntimeError(f"只解析到 {len(rows)} 列，版面可能改版（見 debug）")
        q, ttm, ann = build(rows)
        obj = {"updated": now, "source": "S&P Dow Jones Indices sp-500-eps-est.xlsx", "q": q, "ttm": ttm, "annual": ann, "debug": debug}
        print("OK 季資料", len(q), "筆；近四季", len(ttm), "筆；年度", len(ann), "年")
    except Exception as e:
        print("失敗：", e, file=sys.stderr)
        obj = dict(prev) if prev else {"q": [], "ttm": [], "annual": {}}
        obj["last_error"] = {"at": now, "msg": str(e)}
        if "debug" not in obj:
            obj["debug"] = {}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(obj, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

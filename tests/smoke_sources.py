import sys, time, json
sys.path.insert(0, "backend")
from finn.sources import screener, prices
from finn.config import PORTFOLIO
t = time.time()
c = screener.company("TRENT")
print("TRENT", c["name"], c["company_id"], "| quarters", c["quarters"]["periods"][-3:], "| anns", len(c["announcements"]), f"{time.time()-t:.1f}s")
print(" ann0", json.dumps(c["announcements"][0])[:260])
print(" docs", {k: len(v) for k, v in c["documents"].items()}, "| sales rows", list(c["quarters"]["rows"])[:6])
print(" cash", list(c["cash_flow"]["rows"])[:6], "| eff", list(c["efficiency"]["rows"]))
print(" growth", c["sales_growth"], "| about", c["about"][:80])
for q in ["Infosys", "HDFCBANK", "M&M"]:
    x = screener.company(q); print(q, "->", x["ticker"], x["name"], "anns", len(x["announcements"]))
t = time.time()
e = prices.eod([p["ticker"] for p in PORTFOLIO])
print("prices", f"{time.time()-t:.1f}s", "missing:", [k for k, v in e.items() if not v])
print(" TRENT", {k: v for k, v in (e["TRENT"] or {}).items() if k != "closes"})

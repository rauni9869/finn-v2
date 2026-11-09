import sys, time, json, logging
sys.path.insert(0, "backend")
logging.basicConfig(level=logging.WARNING)
from finn.push import digest
from fastapi.testclient import TestClient
from finn.main import app
c = TestClient(app)
fs = digest.all_filings()
print("total", len(fs))
for f in fs: print(f"{f['priority']:6} {f['category']:18} {f['classified_by']:7} {f['ticker']:10} | {f['title'][:55]:55} | {f['summary'][:70]}")
mg = [f for f in fs if f["category"] == "management_change"]
if mg:
    s = time.time(); r = c.get(f"/api/filings/{mg[0]['id']}/people"); print("\npeople", r.status_code, f"{time.time()-s:.0f}s", json.dumps(r.json())[:800])
s = time.time(); r = c.get("/api/research/SWIGGY/analysis"); j = r.json(); print("\nanalysis", r.status_code, f"{time.time()-s:.0f}s")
if r.status_code == 200:
    print(" cred", j["credibility_pct"], j["coverage"], "| promises", len(j["promises"]), "guidance", len(j["guidance"]), "bull", len(j["bull"]), "bear", len(j["bear"]), "dropped", j["dropped_unverified"])
    for p in j["promises"]: print("  ", p["verdict"], p["transcript"], "p", p["page"], "|", p["promised"][:100])
    for g in j["guidance"]: print("   G", g["topic"], "|", g["target"][:100])
    for p in j["bull"]: print("   +", p["transcript"], "|", p["point"][:100])
    for p in j["bear"]: print("   -", p["transcript"], "|", p["point"][:100])
else: print(j)

import sys, time, json, logging
sys.path.insert(0, "backend")
logging.basicConfig(level=logging.WARNING)
from fastapi.testclient import TestClient
from finn.main import app
from finn.push import digest
c = TestClient(app)
mg = [f for f in digest.all_filings() if f["category"] == "management_change"]
for f in mg[:2]:
    s = time.time(); r = c.get(f"/api/filings/{f['id']}/people"); print("people", f["ticker"], r.status_code, f"{time.time()-s:.0f}s", json.dumps(r.json())[:900], "\n")
s = time.time(); r = c.get("/api/research/SWIGGY/analysis"); j = r.json(); print("analysis", r.status_code, f"{time.time()-s:.0f}s")
if r.status_code == 200:
    print(" cred", j["credibility_pct"], j["coverage"], "| promises", len(j["promises"]), "guidance", len(j["guidance"]), "bull", len(j["bull"]), "bear", len(j["bear"]), "dropped", j["dropped_unverified"])
    for p in j["promises"]: print("  ", p["verdict"], p["transcript"], "p", p["page"], "|", p["promised"][:100])
    for g in j["guidance"]: print("   G", g["topic"], "|", g["target"][:100])
    for p in j["bull"] + j["bear"]: print("   *", p["transcript"], "|", p["point"][:100])
else: print(j)

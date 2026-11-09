import sys, time, json, logging
sys.path.insert(0, "backend")
from fastapi.testclient import TestClient
from finn.main import app
logging.getLogger("httpx").setLevel(logging.WARNING)
c = TestClient(app)
def t(label, fn):
    s = time.time(); r = fn(); print(f"\n## {label} {r.status_code} {time.time()-s:.1f}s"); return r.json()
print(t("health", lambda: c.get("/api/health")))
for h in (24, 48, 168):
    d = t(f"digest {h}h", lambda: c.get(f"/api/digest?window_hours={h}"))
    print(" counts", d["counts"])
for f in d["material"][:12]: print(f"  {f['priority']:6} {f['category']:18} {f['ticker']:10} {f['published_at'][:10]} {f['title'][:60]} | {f['classified_by']}")
for f in d["routine"][:6]: print(f"  LOW    {f['category']:18} {f['ticker']:10} {f['title'][:60]}")
res = [f for f in d["material"] if f["results"]]; print(" with results scorecard:", [(f["ticker"], f["results"]["quarter"]) for f in res][:5])
if res: print(" ", json.dumps(res[0]["results"]["metrics"])[:400])
mg = [f for f in d["material"] if f["category"] == "management_change"]
print(" mgmt filings:", [(f["ticker"], f["title"][:50]) for f in mg][:4])
if mg:
    p = t("people", lambda: c.get(f"/api/filings/{mg[0]['id']}/people")); print(" ", json.dumps(p)[:700])
a = t("alerts default", lambda: c.post("/api/alerts", json={}))
print(" ", [(x["kind"], x["ticker"], x["headline"][:50]) for x in a["alerts"]][:8])
a2 = t("alerts sensitive", lambda: c.post("/api/alerts", json={"volume_multiple": 1.0, "price_move_pct": 0.5}))
print("  market alerts:", sum(1 for x in a2["alerts"] if x["kind"] == "market"))
s = t("search", lambda: c.get("/api/search?q=tata steel")); print(" ", s["results"][:3])
for q in ["TRENT", "HDFCBANK", "Swiggy", "NOTAREALTICKER"]:
    r = t(f"research {q}", lambda: c.get(f"/api/research/{q}"))
    if "snapshot" in r: print(" ", r["ticker"], r["name"], json.dumps(r["snapshot"])[:300], "| traj", r["trajectory"]["periods"][-3:], "| cash", json.dumps({k: v for k, v in r["cash_quality"].items() if "history" not in k}), "| bs", r["balance_sheet"]["debt_to_equity"], "| transcripts", len(r["documents"]["transcripts"]))
    else: print(" ", r)
r = t("analysis TRENT", lambda: c.get("/api/research/TRENT/analysis")); print(" ", str(r)[:200])
r = t("analysis SWIGGY", lambda: c.get("/api/research/SWIGGY/analysis"))
print(" ", r.get("credibility_pct"), r.get("coverage"), "promises", len(r.get("promises", [])), "guidance", len(r.get("guidance", [])), "bull", len(r.get("bull", [])), "bear", len(r.get("bear", [])), "dropped", r.get("dropped_unverified"))
for p in r.get("promises", [])[:3]: print("   ", p["verdict"], p["transcript"], p["page"], "|", p["promised"][:90])
for p in r.get("bull", [])[:2] + r.get("bear", [])[:2]: print("   pt", p["transcript"], "|", p["point"][:90])
for g in r.get("guidance", [])[:3]: print("   g", g["topic"], "|", g["target"][:90])

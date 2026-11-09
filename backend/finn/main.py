import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from finn import llm
from finn.config import AD_HOC, FRONTEND_DIST, PORTFOLIO
from finn.pull import analysis, prewarm, research
from finn.push import alerts, digest, enrich
from finn.sources import prices, screener

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("FINN_PREWARM", "1") != "0":
        prewarm.start()
    yield


app = FastAPI(title="FINN", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "ai": llm.is_available(), "prewarm": prewarm.status()}


@app.get("/api/portfolio")
def portfolio():
    eod = prices.eod([p["ticker"] for p in PORTFOLIO])
    return {"stocks": [{**p, "eod": eod.get(p["ticker"])} for p in PORTFOLIO], "ad_hoc": AD_HOC}


@app.get("/api/digest")
def get_digest(window_hours: int = Query(24, ge=1, le=168), ticker: Optional[str] = None):
    return digest.digest(window_hours, ticker)


@app.post("/api/alerts")
def get_alerts(settings: alerts.AlertSettings):
    return {"alerts": alerts.evaluate(settings)}


@app.get("/api/filings/{filing_id}/people")
def filing_people(filing_id: str):
    filing = next((f for f in digest.all_filings() if f["id"] == filing_id), None)
    if not filing:
        raise HTTPException(404, "Filing not found.")
    if filing["category"] != "management_change":
        raise HTTPException(400, "Only management change filings have a people brief.")
    try:
        return enrich.management_brief(filing["company"], filing["title"], filing["summary"], quick=True)
    except llm.LLMUnavailable as e:
        raise HTTPException(503, str(e))


@app.get("/api/search")
def search(q: str = Query(..., min_length=1, max_length=60)):
    try:
        return {"results": screener.search(q)}
    except Exception:
        raise HTTPException(503, "Search is unavailable right now.")


@app.get("/api/research/{query}")
def get_research(query: str):
    try:
        return research.report(query)
    except screener.CompanyNotFound:
        raise HTTPException(404, f"No company found for '{query}'. Try its NSE ticker or full name.")
    except Exception:
        logging.exception("research failed")
        raise HTTPException(503, "Company data couldn't be loaded right now. Please try again.")


@app.get("/api/research/{query}/analysis")
def get_analysis(query: str):
    try:
        return analysis.analyse(query)
    except screener.CompanyNotFound:
        raise HTTPException(404, f"No company found for '{query}'.")
    except analysis.AnalysisUnavailable as e:
        raise HTTPException(503, str(e))


# The built frontend, so one service hosts the whole app
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

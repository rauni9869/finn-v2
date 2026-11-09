---
title: FINN
emoji: 📈
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Push digest and AI research for Indian equities
---

# FINN v2

A mobile-first investing agent for Indian equities, built for the ENAM Holdings AI Engineer Build Challenge. Everything runs on live data: there are no hand-written samples.

- **Push** tells you what changed across an 18-stock portfolio: exchange filings sorted by importance, routine paperwork collapsed, and alerts on thresholds you set.
- **Pull** researches any NSE company on demand, including an AI check of what management promised against what it delivered, grounded only in the company's own transcripts and reported numbers.

## Data sources

| Data | Source | Notes |
|---|---|---|
| End-of-day price and volume | Yahoo Finance (`yfinance`) | Last completed session. A stock shows "n/a" if Yahoo has no data. |
| Exchange filings | BSE announcements, as listed on screener.in | The latest 5 per company, with screener.in's one-line summaries. NSE and BSE block automated access to their own APIs, so FINN does not scrape them directly. |
| Financials, ratios, document links | screener.in | Standardised from company filings. Covers any listed company. |
| Earnings call transcripts | BSE PDFs linked from screener.in | Read page by page for the AI analysis. |
| People background | Groq (`gpt-oss`) with web search | Only for management-change filings, with links to the pages it read. |

## How the AI is used

| Job | Model | Why |
|---|---|---|
| Filing categories | Keyword rules first; `gemini-flash-lite` only for filings the rules miss, in one batched call | Most filings are labelled by the filer, so rules are free and instant |
| Promises vs delivery, guidance, bull vs bear | `gemini-flash` with fallbacks | Needs reasoning over long transcripts |
| Who joined or left | Groq `gpt-oss-120b` with web search, falling back to `gpt-oss-20b`, then Gemini | Needs current facts with sources, and keeps Gemini's small daily limit for the transcript analysis |

Safeguards:
- **Only primary sources:** the research model sees only the company's transcripts and reported numbers, and is told not to use outside knowledge.
- **Quote check:** every promise, guidance item and bull or bear point must quote the transcript word for word. FINN checks each quote against the cited page and removes any it can't find.
- **Caching:** results are cached, and the transcript analysis refreshes only when a new transcript appears.
- **Busy models:** a busy model is retried once, then the next model is tried.

## Run it

You need Python 3.10+ and Node.js 18+. Keep the project outside folders synced to iCloud, such as Desktop or Documents, because offloaded files make it very slow.

```bash
python3.12 run.py
```

Open http://localhost:3000. The first run installs everything. To turn on the AI features, create a `.env` file in this folder with `GEMINI_API_KEY=your_key`, and optionally `GROQ_API_KEY=your_key` for faster people briefs.

## Deploy (Hugging Face Spaces)

The `Dockerfile` builds the frontend and serves everything from FastAPI on port 7860, which is what Hugging Face Spaces expects. The free tier gives 2 vCPUs and about 16 GB of RAM, and stays awake far longer than Render's free tier, so the background pre-run keeps results ready.

1. Create a Space at https://huggingface.co/new-space, choose **Docker** and **Blank**, and leave it public or private as you prefer.
2. In the Space's **Settings → Variables and secrets**, add a secret `GEMINI_API_KEY`.
3. Push this repository to the Space's git remote. Hugging Face builds and starts it.

`render.yaml` is kept for Render as an alternative.

## Speed

- **Pre-run:** on startup, and every 6 hours, FINN analyses the 18 holdings and the suggested companies in the background, one every 20 seconds. Those open instantly. `/api/health` shows progress.
- **Low reasoning:** Gemini is asked for low hidden reasoning, which answers in seconds rather than minutes.
- **Fallback:** a model that doesn't answer within 90 seconds is retried once, then the next model is tried.
- **Snapshots:** finished analyses and people briefs are also saved as JSON in `snapshots/`, which is committed to the repo. After a restart or redeploy, FINN loads them instead of asking Gemini again, so only new transcripts and new companies use quota. To add results made on your machine, run `PYTHONPATH=backend .venv/bin/python scripts/export_snapshots.py` and commit `snapshots/`.

## Structure

```
backend/finn/
  main.py            API routes; serves the built frontend
  config.py          Portfolio, model choices, paths
  cache.py           Disk cache with per-key locking
  llm.py             Gemini calls, JSON output, retries and fallbacks
  sources/           screener.in and Yahoo Finance
  push/              classify.py, digest.py, alerts.py, enrich.py
  pull/              research.py (figures), analysis.py (AI from transcripts)
frontend/src/
  views/             Today, Research, Portfolio
  components/        FilingCard, BarChart
tests/               Smoke tests against live data
```

## Known limits

- Only the 5 most recent filings per company are available, so a busy filer's older filings can drop out of the 7-day view.
- Filing summaries are screener.in's, and are labelled as such.
- AI verdicts can be wrong even when the quote is real. Every item links to its transcript page.
- The first analysis of a company takes one to two minutes, and the free Gemini tier can be busy.

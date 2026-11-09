**To:** assessment@enam.com
**Subject:** ENAM - IIT screening - 2027

Dear ENAM team,

Please find my submission for the AI Engineer Build Challenge.

- **Live prototype (opens on a phone):** https://finn-v2.onrender.com
- **Repository:** https://github.com/rauni9869/finn-v2
- **AI build history:** summarised in [BUILD_HISTORY.md](https://github.com/rauni9869/finn-v2/blob/main/BUILD_HISTORY.md). It covers how I broke the problem down, prompted, course-corrected and decided what to accept. The full records are attached: the Claude Code session export, and the Antigravity session, also in the repo's `ai-history` folder.

The site is on free hosting, so the first visit after a quiet spell can take up to a minute.

## What I built
FINN is a mobile-first assistant for an investor holding 18 NSE stocks across sectors and sizes, running entirely on live data.

- **Push (Today):** exchange filings for the last 24 hours, 48 hours or 7 days, sorted into the 17 reference categories and ranked so the important ones come first, with routine paperwork folded away.
  - **Results filings** get a first cut of Revenue, EBITDA, PBT and PAT, QoQ and YoY.
  - **Management changes** get a web-searched background on the person, with sources.
  - **Alerts** fire on volume spikes, price moves and chosen filing types, with thresholds the investor sets.
- **Pull (Research):** any NSE company, by ticker or name: business, financial snapshot, eight-year trajectory, balance sheet, cash quality and primary documents.
  - **Promises vs delivery** is the centrepiece. FINN reads the last four earnings call transcripts, finds specific promises, checks them against what happened, and quotes the transcript page for each.

## Key decisions and trade-offs
- **Live data over a polished demo.** My first version passed its tests on hand-written sample data. A review exposed invented reports and a fixed score, so I rebuilt on live data only, accepting gaps where data is unavailable.
- **Checkable AI over more AI.** Every AI quote is verified against the transcript page and dropped if it can't be found. A delivery score needs at least 3 checked promises. I chose to show fewer items rather than unverified ones.
- **Honest sourcing over workarounds.** NSE and BSE block automated access to their feeds, so I used screener.in's copy of BSE announcements instead of getting around their bot protection. The trade-off is only 5 recent filings per company.
- **Built for free tiers.** Gemini's free plan allows 20 requests a day. Background preparation, saved results and model routing keep FINN within it, at the cost of some complexity.

## Architecture
- **Data pipelines.**
  - **Sources:** Yahoo Finance for end-of-day prices (cached 1 hour) and screener.in for filings, financials and transcript links (cached 6 hours).
  - **Push:** filings are classified by keyword rules, with an AI fallback, then prioritised, enriched and served.
  - **Pull:** transcript PDFs are split page by page, analysed, quote-checked, then saved.
- **LLMs and agents.** Each job goes to the cheapest model that does it well:
  - **Rules** sort most filings.
  - **Gemini Flash-Lite** sorts the leftovers in one batched call.
  - **Gemini 3 Flash** reasons over about 200 pages of transcripts, with low "thinking" settings, taking about 20 seconds.
  - **Groq's open `gpt-oss` models** search the web for people briefs, which keeps Gemini's small allowance for research.
  - **Reliability:** models fall back to one another and fail fast when someone is waiting. FINN uses fixed pipelines with tools rather than an open-ended agent loop, which keeps cost and behaviour predictable.
- **Security and privacy.**
  - **Keys:** API keys live only in environment variables, on Render and in a git-ignored `.env`, and have never been committed.
  - **Data:** FINN uses only public market data. It has no accounts and stores no personal data, and its saved results contain only public company information.
  - **Known gaps:** the API allows requests from any website (open CORS) and has no rate limiting, so someone could use up the AI quota. Both are next steps.
- **Cloud.**
  - **Hosting:** one Render free web service serves both the API and the built website.
  - **Uptime:** an uptime monitor stops the free tier from sleeping.
  - **Storage:** Render's disk is wiped on restart, so finished AI results are committed to the repository as snapshots and reloaded, and redeploys don't spend AI quota.
  - **Portability:** a Dockerfile lets the same service run anywhere.

## What I deliberately left out
- **A direct exchange feed,** since NSE and BSE block automated access.
- **User accounts and server-side portfolios:** the portfolio is fixed and alert settings live in the browser, which avoids storing personal data.
- **Phone push notifications:** alerts appear in the app.
- **AI on every view:** balance sheet and cash quality are calculated from reported numbers rather than generated.

## Where I'd take it next
1. **A licensed filings feed** for complete coverage, with real phone notifications for alerts.
2. **Rate limiting and restricted CORS,** plus a paid AI tier with a spending cap, so the AI features are reliable under real traffic.
3. **Tracking guidance across quarters,** and flagging when management's tone or targets shift.

A note on timing: the challenge deadline was 1 November. My first version and its review were done by then; the version linked above was rebuilt afterwards, on 9 November.

Thank you for your time.

Raunak Raj

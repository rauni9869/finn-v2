# Covering note (draft: edit before sending)

**To:** assessment@enam.com
**Subject:** ENAM - IIT screening - 2027

Dear ENAM team,

Please find my submission for the AI Engineer Build Challenge.

- **Live prototype (works on a phone):** https://finn-v2.onrender.com
- **Repository:** https://github.com/rauni9869/finn-v2
- **AI build history:** BUILD_HISTORY.md in the repository summarises both sessions (Antigravity for version 1, Claude Code for the review and version 2). The full records are in the repository's ai-history folder and attached

The site is on free hosting, so the first visit after a quiet spell can take up to a minute to load.

## What I built
FINN is a mobile-first assistant for an investor holding 18 NSE stocks across sectors and sizes. It runs entirely on live data.

- **Push (Today):** filings from the exchange for the last 24 hours, 48 hours or 7 days, sorted into the 17 reference categories and ranked so the important ones come first, with routine paperwork folded away. Results filings get a first cut of Revenue, EBITDA, PBT and PAT, QoQ and YoY. Management changes get a short background on the person from a web search, with sources. Alerts fire on volume spikes, price moves and chosen filing types, with thresholds the investor sets.
- **Pull (Research):** any NSE company, by ticker or name: business, financial snapshot, multi-year trajectory, balance sheet, cash quality and primary documents. The centrepiece is **promises vs delivery**: FINN reads the last four earnings call transcripts, finds specific promises, and checks them against what later happened, quoting the transcript page for each.

## Key decisions and trade-offs
- **Grounded, checkable AI.** The research model sees only the company's own transcripts and reported numbers. Every quote it returns is checked against the actual transcript page, and any quote that can't be found is dropped. I chose to show fewer items rather than unverified ones.
- **Right model for each job.** Simple rules sort most filings for free; a small model handles only the leftovers. Gemini Flash does the long-document reasoning with low "thinking" settings, which cut an analysis from about two minutes to about 20 seconds. Groq's open models handle the web-searched people briefs, which keeps Gemini's small free allowance for the research.
- **Built for the free tier.** Gemini's free plan allows 20 requests a day. FINN prepares the portfolio's analyses in the background, saves them permanently, and re-runs a company only when a new transcript appears, so it stays within that limit.
- **Honest gaps over invented answers.** An unknown ticker gets "no company found", and a company without usable transcripts says so instead of showing a made-up score.
- **Data sources.** NSE and BSE block automated access to their own feeds, so I used screener.in's copy of BSE announcements rather than working around those blocks.

## What I deliberately left out
- **The full exchange feed:** filings come from screener.in, which lists only the latest 5 per company.
- **Push notifications:** alerts are shown in the app rather than sent to the phone.
- **AI analysis for every research view:** balance sheet and cash quality are calculated from reported numbers, not AI-generated.

## Where I'd take it next
1. Connect a direct, licensed filings feed for complete coverage.
2. Send real push notifications for alerts.
3. Extend the transcript analysis to track guidance over time, and flag when management's tone changes.

Thank you for your time.

Raunak Raj

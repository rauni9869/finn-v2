# FINN

**FINN is a phone-friendly assistant for people who invest in Indian stocks.** It watches a portfolio for you and tells you what changed, and when you want to dig into a company, it reads the company's own documents and shows you whether management has done what it said it would.

Built for the ENAM Holdings AI Engineer Build Challenge. Everything runs on live data, with no made-up samples.

**Try it:** https://finn-v2.onrender.com

> It runs on free hosting, so the very first visit after a quiet spell can take up to a minute to wake up.

---

## The problem it solves

An investor is flooded with information: price moves, stock-exchange filings, results, management changes. Most of it doesn't matter. FINN's job is to **surface the few things that do, and hide the rest.**

It works in two ways:

| Mode | What it means | Where in the app |
|---|---|---|
| **Push** | FINN tells you what changed, without being asked | **Today** page |
| **Pull** | You ask FINN to research a company | **Research** page |

---

## A quick tour

### Today: what changed
- **Filings, sorted by importance.** Every announcement your 18 companies filed with the stock exchange, for the last 24 hours, 48 hours or 7 days. Important ones, such as results, acquisitions or a new CEO, come first. Routine paperwork is folded away.
- **Results at a glance.** When a company reports quarterly results, FINN shows Revenue, EBITDA, PBT and PAT, compared with the previous quarter and the same quarter last year.
- **Who is this?** When a company appoints or loses a senior person, FINN looks them up on the web and shows a short background, with links to where it found it.
- **Alerts you control.** Get alerted when a stock trades far more than usual or moves sharply in a day, or when a company files something you care about. You set the thresholds with sliders.
- **Brief me.** Plays a short spoken summary, handy on a commute.

### Research: dig into any company
Search any company listed on the NSE, by ticker or by name, and get:
- **The basics:** what the company does, its key numbers, eight years of revenue and profit as charts, and the last eight quarters.
- **Promises vs delivery.** FINN reads the company's last four earnings calls and finds specific promises management made, such as "we'll break even next quarter". It then checks what actually happened and marks each one *delivered*, *partial*, *delayed*, *missed* or *diverged*, with the exact quote and a link to the transcript page. If enough promises can be checked, it gives an overall **delivery score**.
- **Guidance and a bull vs bear case,** each backed by a quote or the reported numbers.
- **Balance sheet and cash quality:** how much the company borrows, and whether its profits turn into real cash.
- **Links to the original documents:** annual reports, call transcripts and presentations.

### Portfolio
Each holding's latest closing price, daily move, trading volume against its usual level, and a 30-day trend line. Tap any company to research it.

---

## How it works

```
  Live data                       FINN                          You
  ─────────                       ────                          ───
  Stock prices (Yahoo)   ─┐
  Exchange filings       ─┼──►  Sort, prioritise, alert  ──►  Today page
  Company financials     ─┤
  Earnings call PDFs     ─┼──►  AI reads transcripts,    ──►  Research page
  Web search             ─┘     checks every quote
```

1. **Collect.** FINN fetches end-of-day prices from Yahoo Finance, and company filings, financials and transcript links from screener.in.
2. **Filter.** Filings are sorted into categories and ranked by importance, mostly with simple rules. A small AI model handles only the ones the rules can't place.
3. **Analyse.** For research, an AI model reads the company's transcripts and reported numbers, and nothing else, then lists promises and outcomes.
4. **Verify.** FINN checks every quote the AI gives against the actual transcript page and throws away any it can't find. This keeps the AI from inventing quotes.
5. **Remember.** Results are saved, so they appear instantly next time and don't use up the free AI allowance again.

### Which AI does what

| Task | Model | Why this one |
|---|---|---|
| Sorting filings | Rules first, then Gemini Flash-Lite for the leftovers | Cheapest option; most filings are easy to sort by rules |
| Promises vs delivery | Gemini 3 Flash, falling back to Gemini Flash | Needs careful reasoning over about 200 pages |
| Who joined or left | Groq `gpt-oss-120b` with web search, falling back to `gpt-oss-20b` | Needs up-to-date facts with sources, and keeps Gemini's small allowance for the research |

### Where the data comes from

| Data | Source |
|---|---|
| Daily prices and volume | Yahoo Finance |
| Exchange filings | BSE announcements, via screener.in (the latest 5 per company) |
| Financials and document links | screener.in, standardised from company filings |
| Earnings call transcripts | PDFs linked from screener.in, mostly on BSE |
| People backgrounds | Web search through Groq |

The NSE and BSE block automated access to their own feeds, so FINN uses screener.in's copy of BSE announcements instead of getting around those blocks.

---

## Keeping it fast on free AI plans

The free AI plans are small: Gemini allows **20 requests a day**, and Groq allows **200,000 tokens a day** per model. FINN is designed to fit inside them:

- **Done in advance.** When FINN starts, and every 6 hours, it prepares the people briefs and analyses all 18 holdings, plus 4 suggested companies (Swiggy, Dixon, Eternal and BEL), in the background. Opening them is instant.
- **Saved permanently.** Finished results are stored in the `snapshots/` folder in this repository, so a restart doesn't redo them. A company is re-analysed only when it publishes a new transcript.
- **Quick answers.** A new analysis takes about 20 seconds. If an AI service is busy, FINN gives up quickly and says so, rather than leaving you waiting.

You can see background progress at `/api/health`, for example https://finn-v2.onrender.com/api/health. There, **done** means ready to open instantly, **skipped** means the company has no usable transcripts, and **waiting** means it's queued until the AI allowance resets.

---

## Run it yourself

You need **Python 3.10+** and **Node.js 18+**.

1. Get two free API keys:
   - Gemini: https://aistudio.google.com/apikey
   - Groq: https://console.groq.com
2. Create a file called `.env` in the project folder:
   ```
   GEMINI_API_KEY=your_gemini_key
   GROQ_API_KEY=your_groq_key
   ```
   Without these keys, everything except the AI features still works.
3. Start it:
   ```bash
   python3.12 run.py
   ```
4. Open http://localhost:3000. The first run installs everything automatically. Press `Ctrl+C` to stop.

**Tips**
- On a Mac, keep the project outside iCloud-synced folders such as Desktop or Documents. iCloud can offload files, which makes the app very slow.
- If a deployed copy uses the same keys, run the local one without the background work, so they don't share the daily allowance:
  ```bash
  FINN_PREWARM=0 python3.12 run.py
  ```
- To save AI results made on your machine into `snapshots/`, then commit them:
  ```bash
  PYTHONPATH=backend .venv/bin/python scripts/export_snapshots.py
  ```

## Put it online

The live site runs on **Render's free plan**:
1. In Render, create a **Blueprint** from this repository. `render.yaml` sets up one web service that builds the website and runs the backend.
2. Paste your `GEMINI_API_KEY` and `GROQ_API_KEY` when asked.
3. Render's free plan sleeps after 15 minutes without visitors. To keep it awake, add a free monitor, such as UptimeRobot, that opens `/api/health` every 5 minutes.

A `Dockerfile` is also included, if you'd rather run it as a container. It serves on port 7860.

---

## Project layout

```
backend/finn/
  main.py          The web API; also serves the website and starts the background work
  config.py        The portfolio, AI model choices and file paths
  cache.py         Saving results, including the permanent snapshots
  llm.py           Talking to Gemini and Groq, with retries and fallbacks
  sources/         Fetching data from screener.in and Yahoo Finance
  push/            Today page: sorting filings, alerts, results first cut, people briefs
  pull/            Research page: figures, AI transcript analysis, background preparation
frontend/src/
  views/           The Today, Research and Portfolio pages
  components/      Filing cards and charts
snapshots/         Saved AI results, reused after restarts
scripts/           export_snapshots.py
tests/             Quick check scripts that call the live data sources
```

## Known limitations

- **Filings:** only the 5 most recent per company are available, so a company that files a lot may have older filings missing from the 7-day view.
- **Summaries:** the one-line filing summaries come from screener.in.
- **No analysis for three holdings:** ITC and Trent have no transcripts on screener.in, and Federal Bank's transcript links lead to web pages rather than PDFs.
- **AI can still be wrong:** a verdict can be wrong even when its quote is real. Every item links to the transcript page so you can check it.
- **Free AI limits:** on a busy day, a first-time analysis of a new company may be refused until the daily allowance resets. FINN says so and tries again later.

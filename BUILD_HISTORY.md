# FINN: AI build history

How I built FINN with AI coding agents, from first plan to the live app. This page summarises two real sessions; the full records are in [`ai-history/`](ai-history/) and attached to my submission.

| | Version 1 | Version 2 (submitted) |
|---|---|---|
| **Agent** | Antigravity (Google DeepMind) | Claude Code (Anthropic) |
| **Dates** | 31 Oct – 3 Nov 2026 | 1 Nov and 9 Nov 2026 |
| **Record** | [`ai-history/01-antigravity-v1-history.md`](ai-history/01-antigravity-v1-history.md) | Full session export, attached separately |
| **Outcome** | A broad prototype, mostly on hand-written sample data | A rebuild on live data, deployed at https://finn-v2.onrender.com |

**How I worked with the agents:** I set the direction, reviewed and tested what they produced, and made the product and trade-off decisions. The agents planned, investigated and wrote most of the code.

---

## Part 1: Planning and the first version (Antigravity, 31 Oct – 1 Nov)

**1. Plan first.** I asked the agent, acting as a senior engineer, to turn the two challenge PDFs into a detailed `plan.md`: architecture, an 18-stock portfolio plus 4 out-of-portfolio tickers, the 17 filing categories, both push enrichments, all 8 research dimensions, and model routing.

**2. Review the plan before building.** I had the plan audited line by line against both PDFs. The review found gaps, including no related-party transaction check and no investor presentations as a document type. It also flagged the main risk: **too much scope for five days**, against the brief's "thin-but-working beats broad-but-broken". I had the plan revised with an explicit MVP-versus-stretch split and fallback data in case scraping failed.

**3. Build.** The agent built a FastAPI backend and a React frontend covering the plan: a windowed digest, alerts with sliders, the results first cut and management bio, eight research tabs led by promises vs delivery, and a spoken briefing.

**4. Question the data.** I asked whether the required scraping was actually done, then asked specifically whether Screener.in scraping worked. The agent confirmed live Screener.in data for Trent, Polycab, Dixon and Tata Motors, and wired the document links into a "Primary Vault" tab.

**5. Make it runnable and refine the design.** I had a setup guide and a one-command launcher written so a friend could run it. I then pushed for a design that didn't look AI-generated, and later asked for a full light-mode redesign when the first pass didn't change enough.

---

## Part 2: Reviewing version 1 (Claude Code, 1 Nov)

I brought the version-1 code to a second agent and asked it to go through every file and check the app against the brief. The review found that **much of version 1 looked better than it was:**

- Its tests reported "100% success", but they ran on hand-written sample data. Even the earlier scraping check printed a price of ₹1,000.00 and volume of 500,000, which were the app's fallback values, not live data.
- **Unknown tickers got invented research reports**, and every company showed the same hard-coded "92%" credibility score.
- The alert sliders called an endpoint that didn't exist, and the 24h/48h/7-day filter showed the same filings every time.
- Several alerts were forced: three stocks always showed preset price moves.

I had these fixed: unknown tickers return "no company found", the score is calculated, alerts use real prices, and the sliders and window work. I then added a first AI analysis of real transcripts with Gemini, deployed it, and tested it on Swiggy.

**Lesson:** an agent's "all tests pass" is not evidence. I now check the output, not the summary. This shaped everything in Part 3.

---

## Part 3: Rebuilding on live data (Claude Code, 9 Nov)

I decided to keep version 1 untouched and **build a new version from scratch, using live data only**. I chose to keep FastAPI and React, and to make live data end to end the first priority.

### Data sources, chosen honestly
- Testing showed that **NSE refuses automated connections and BSE returns "Access Denied"**. Rather than work around their bot protection, I used screener.in, which lists each company's BSE announcements with links to the original filings, alongside financials and transcript links. Prices come from Yahoo Finance.
- Accepted trade-off: screener.in lists only the latest 5 filings per company. This is stated in the app.

### Making the AI trustworthy
- The research model receives **only the company's own transcripts and reported numbers**.
- **Every quote it returns is checked against the cited transcript page**, and anything not found is removed.
- When a weak fallback model gave a "100%" score from a single promise, I required **at least 3 checked promises before showing a score** and removed that model from the job.
- A people brief from the model's memory gave a wrong employer for an executive, and a web-searched brief found the right background. **Briefs now use web search and link their sources.**

### Fixing what testing found
- **Empty company pages:** Supriya Lifescience has no consolidated accounts, and screener.in's empty consolidated page wasn't detected. Fixed, then all 18 holdings were checked.
- **A "frozen" machine:** a type check that takes seconds never finished. The cause was **iCloud offloading the project's library files**. Moving the project out of the synced Desktop cut backend start-up from about 90 seconds to 5.
- **Back button:** added at the top of each page, then moved into the sticky header after I found it unreachable on long pages.

### Speed
- I asked for the 1–2 minute analysis wait to go. Measurements showed the main model timing out while another answered in **3 seconds with reduced reasoning**; after switching, **an analysis takes about 20 seconds**.
- Holdings and people briefs are **prepared in the background** before anyone opens them, so they appear instantly.

### Working within free AI limits
- The logs showed Gemini's free tier allows only **20 requests a day** per model, and every redeploy was recomputing everything.
- **Snapshots:** finished AI results are saved in the repository and reloaded after restarts, so only genuinely new work uses quota.
- **Model routing:** I added **Groq** (open `gpt-oss` models with built-in web search) for people briefs, keeping Gemini's allowance for the long transcript analysis. Groq's 8,000-tokens-per-minute free limit made it unsuitable for the analysis itself.

### Design and hosting
- I chose arcprize.org as the visual reference: dark and minimal, with monospace labels. I removed introductory headings that pushed content down.
- Hugging Face's Docker hosting turned out to need a paid plan, so the app runs on **Render's free tier** with an uptime monitor to stop it sleeping.

---

## What I'd do differently
- **Verify early, not at the end.** Version 1's passing tests hid sample data for days. I'd check real output from the first working feature onwards.
- **Check free-tier limits on day one.** They shaped the final architecture late in the build.
- **Keep projects out of iCloud-synced folders** from the start.

## A note on timing
The challenge deadline was 1 November. Version 1 and the first review were done by then; version 2 was built afterwards, on 9 November.

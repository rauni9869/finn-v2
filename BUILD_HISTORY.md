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

## How I work with AI tools

### Breaking problems down
- **Plan, then audit, then build.** In version 1, I had the brief turned into a plan, had that plan reviewed against both PDFs, and only then started building. The review caught gaps and forced an MVP-versus-stretch split.
- **Check the riskiest assumption first.** In version 2, before any code, I had the data sources tested: NSE, BSE, screener.in and Gemini. Two exchange feeds turned out to be blocked, which changed the design before anything was built on them.
- **Build in layers and check each one.** Data sources, then the Push logic, then Pull, then the frontend, with a live smoke test after each layer.

### Prompting
I give the problem and the outcome I want, often from what I see as a user, rather than a solution. Real prompts from the sessions:
- *"act as a senior SWE"* and *"verify the plan"*: setting the role and asking for critique, not agreement.
- *"is this site working fine according to the things asked in this file"*: checking against the brief, not against the agent's own summary.
- *"I wish to see a UI which doesn't seem as if it is made by an AI agent"*: a quality bar, not a spec.
- *"it is not good for users, they won't wait for so much time"*: a user problem, which led to background preparation and a 20-second analysis.
- *"in any particular page if it is very large the back button will only appear when going to the top"*: a specific usability bug from using the app.

### Course-correcting when the model went wrong
- **Version 1 claimed "100% success" on sample data.** I had a second agent review every file; it found invented reports, a fixed 92% score and broken sliders.
- **The AI-analysis build wasn't reliable live, so I rolled back.** Instead of submitting something broken, I redeployed the earlier version, then planned a clean rebuild.
- **The agent recommended free Docker hosting on Hugging Face.** I pointed out it is paid; the agent checked, confirmed I was right, and we moved to Render.
- **The agent wrote filler headings and introductions.** I had them removed: *"this should not be written, why are you writing this."*
- **A fallback model gave a "100%" score from one promise.** We added a minimum of 3 checked promises before any score is shown.
- **An AI-written bio named the wrong employer.** Briefs moved to web search with sources.

### Deciding what to accept and what to reject
- **Accepted** when the agent showed evidence: measured timings, logs showing the 20-requests-a-day limit, or a test with an empty cache and an invalid key proving the snapshots work.
- **Rejected** claims I couldn't verify, such as "live scraping verified" with fallback numbers in the output, and options that cut quality to save cost. For example, I didn't use the weaker model for the analysis just to stay free.
- **I didn't hand-write much code.** My "rewrites" were redirections: rejecting an output, saying what was wrong, and having it redone, then checking the result in the browser or the logs.

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

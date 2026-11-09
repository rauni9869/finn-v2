# Build log: how I built FINN with an AI coding agent

A short summary of the real build history. I worked with **Claude Code**: I set the direction, tested the app, and made the product and trade-off decisions; Claude proposed options, investigated problems, and wrote most of the code. The full, unedited conversation is attached separately.

## 1. Reviewing the first version (1 November)
- I started from an earlier prototype and asked for a review against the brief and the reference PDF.
- The review found serious problems: unknown tickers got **invented research reports**, every company showed a **hard-coded "92%" score**, the alert sliders called an endpoint that didn't exist, and the time-window filter did nothing.
- I had these fixed, and added an AI promises-vs-delivery analysis. I then concluded that patching wasn't enough and **decided to rebuild from scratch on live data only**, keeping the old version untouched.

## 2. Choosing data sources honestly (9 November)
- Testing showed that **NSE refuses automated connections and BSE returns "Access Denied"**. Rather than work around their bot protection, I used screener.in, which lists each company's BSE announcements with links to the original filings, alongside its financials and transcript links. Prices come from Yahoo Finance.
- Trade-off accepted: screener.in shows only the latest 5 filings per company. This is stated in the app and the README.

## 3. Making the AI trustworthy
- The research model receives **only the company's own transcripts and reported numbers**.
- **Every quote the model returns is checked against the cited transcript page**, and anything not found is removed.
- An early run used a weak fallback model and produced a "100%" score from a single promise. So a **score is now shown only when at least 3 promises can be checked**, and the weak model was removed from that job.
- People briefs from the model's memory gave a wrong employer for one executive. A web-searched version found the right background. So briefs now **use web search and link their sources**.

## 4. Fixing what testing found
- **Empty company pages:** Supriya Lifescience has no consolidated accounts, and screener.in's empty consolidated page wasn't caught. Fixed, then all 18 holdings were checked.
- **The machine "freezing":** a type check that should take seconds never finished. The cause was **iCloud offloading the project's library files**. Moving the project out of the iCloud-synced Desktop cut backend start-up from about 90 seconds to 5.
- **Back button:** first added at the top of each page, then moved into the sticky header after I found it unreachable on long pages.

## 5. Speed
- I asked for the 1–2 minute wait to be removed. Measurements showed the main model timing out, while another answered in **3 seconds with reduced reasoning**. After switching, **analyses take about 20 seconds**.
- Holdings are now **analysed in the background** before anyone opens them, and people briefs are prepared the same way, so they open instantly.

## 6. Working within free AI limits
- The logs showed Gemini's free tier allows only **20 requests a day** per model, and every redeploy was recomputing everything.
- **Snapshots:** finished AI results are saved in the repository and reloaded after restarts, so only genuinely new work uses quota.
- **Model routing:** I added **Groq** (open `gpt-oss` models with built-in web search) for the people briefs, keeping Gemini's small allowance for the long transcript analysis. Groq's 8,000-tokens-per-minute free limit made it unsuitable for the analysis itself.

## 7. Design and hosting
- I chose arcprize.org as the visual reference: a dark, minimal style with monospace labels. I also removed introductory headings that pushed content down.
- **Hosting:** Hugging Face's Docker hosting turned out to need a paid plan, so the app runs on **Render's free tier**, with an uptime monitor to stop it sleeping.

## What I'd do differently
- **Check the free-tier limits on day one,** before designing around a model. They shaped the whole architecture late in the build.
- **Keep projects out of iCloud-synced folders** from the start.

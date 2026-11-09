import React, { useEffect, useRef, useState } from 'react';
import { Analysis, api, ApiError, Cited, Report } from '../api';
import { BarChart } from '../components/BarChart';
import { crore, num, pct, times, tone } from '../format';

const SUGGESTED = ['SWIGGY', 'DIXON', 'TRENT', 'HDFCBANK', 'ETERNAL', 'BEL'];

// The URL hash holds the route, so in-page links scroll instead of changing it
const jump = (id: string) => (e: React.MouseEvent) => {
  e.preventDefault();
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

const Source: React.FC<{ c: Cited }> = ({ c }) =>
  c.url ? (
    <a className="label" href={c.url} target="_blank" rel="noopener noreferrer">{c.transcript} transcript{c.page ? `, p. ${c.page}` : ''} ↗</a>
  ) : (
    <span className="label">Reported numbers</span>
  );

function SearchBox({ onPick }: { onPick: (q: string) => void }) {
  const [q, setQ] = useState('');
  const [results, setResults] = useState<{ ticker: string; name: string }[]>([]);
  const [open, setOpen] = useState(false);
  const latest = useRef(0);

  useEffect(() => {
    const query = q.trim();
    if (query.length < 2) { setResults([]); return; }
    const id = ++latest.current;
    const timer = setTimeout(async () => {
      try {
        const res = await api.search(query);
        if (id === latest.current) setResults(res.results);
      } catch { /* suggestions are optional */ }
    }, 250);
    return () => clearTimeout(timer);
  }, [q]);

  const pick = (value: string) => { setQ(''); setResults([]); setOpen(false); onPick(value); };

  return (
    <form style={{ position: 'relative' }} onSubmit={(e) => { e.preventDefault(); if (q.trim()) pick(q.trim()); }}>
      <input
        className="input" value={q} placeholder="Search any NSE company or ticker"
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 150)}
        aria-label="Search company" autoComplete="off" enterKeyHint="search"
      />
      {open && results.length > 0 && (
        <div className="card" style={{ position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0, zIndex: 10, padding: 6 }}>
          {results.map((r) => (
            <button key={r.ticker} type="button" className="row between" style={{ width: '100%', padding: '8px 10px', borderRadius: 8 }} onMouseDown={() => pick(r.ticker)}>
              <span>{r.name}</span><span className="label">{r.ticker}</span>
            </button>
          ))}
        </div>
      )}
    </form>
  );
}

function AnalysisSection({ ticker, onResult }: { ticker: string; onResult: (a: Analysis | null) => void }) {
  const [state, setState] = useState<'loading' | 'done' | 'error'>('loading');
  const [data, setData] = useState<Analysis | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState('loading'); setData(null); onResult(null);
    api.analysis(ticker)
      .then((a) => { if (!cancelled) { setData(a); setState('done'); onResult(a); } })
      .catch((e) => { if (!cancelled) { setError((e as Error).message); setState('error'); } });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker, attempt]);

  if (state === 'loading') {
    return (
      <section className="section" id="promises">
        <h2>Promises vs delivery</h2>
        <div className="row muted" style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }}>
          <span className="spinner" style={{ marginTop: 5 }} />
          <span>Reading the last four earnings call transcripts. Your holdings are analysed ahead of time, so this wait is usually only for a company being opened for the first time.</span>
        </div>
        <div className="skeleton" style={{ height: 140 }} />
      </section>
    );
  }
  if (state === 'error' || !data) {
    return (
      <section className="section" id="promises">
        <h2>Promises vs delivery</h2>
        <p className="muted">{error}</p>
        {/busy|try again|unreadable/i.test(error) && (
          <button className="label" style={{ justifySelf: 'start' }} onClick={() => setAttempt(attempt + 1)}>Try again</button>
        )}
      </section>
    );
  }

  return (
    <>
      <section className="section" id="promises">
        <div className="section-head">
          <h2>Promises vs delivery</h2>
          <span className="label">{data.coverage} transcripts</span>
        </div>
        <p>{data.summary}</p>
        {data.promises.length === 0 && <p className="muted">No promise could be checked against later results.</p>}
        {data.promises.length > 0 && data.credibility_pct === null && (
          <p className="notice">Only {data.promises.length} checkable {data.promises.length === 1 ? 'promise' : 'promises'} found, too few for a delivery score.</p>
        )}
        <div className="stack">
          {data.promises.map((p, i) => (
            <article key={i} className="card stack" style={{ gap: 8 }}>
              <div className="row between"><span className="label">{p.transcript} call</span><span className={`verdict ${p.verdict}`}>{p.verdict}</span></div>
              <h3 style={{ fontWeight: 400 }}>{p.promised}</h3>
              <p className="quote">“{p.quote}”</p>
              <p style={{ fontSize: 14 }}><span className="label accent">Outcome </span>{p.actual_delivered}</p>
              <Source c={p} />
            </article>
          ))}
        </div>
        <p className="label faint">
          AI-generated by Gemini from the transcripts and reported numbers only · every quote is checked against the cited page
          {data.dropped_unverified > 0 && ` · ${data.dropped_unverified} unverifiable items removed`} · verdicts can still be wrong
        </p>
      </section>

      <section className="section" id="guidance">
        <h2>Guidance</h2>
        {data.guidance.length === 0 ? <p className="muted">No explicit guidance found in the latest call.</p> : (
          <div className="stack">
            {data.guidance.map((g, i) => (
              <div key={i} className="stack" style={{ gap: 4, paddingBottom: 10, borderBottom: '1px solid var(--line-faint)' }}>
                <span className="label accent">{g.topic}</span>
                <span>{g.target}</span>
                <Source c={g} />
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section" id="bull-bear">
        <h2>Bull vs bear</h2>
        <div className="stack" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}>
          {([['Bull', data.bull, 'var(--up)'], ['Bear', data.bear, 'var(--down)']] as const).map(([label, points, color]) => (
            <div key={label} className="card stack" style={{ gap: 10 }}>
              <span className="label" style={{ color }}>{label} case</span>
              {points.length === 0 && <span className="muted" style={{ fontSize: 14 }}>None that could be verified.</span>}
              {points.map((p, i) => (
                <div key={i} className="stack" style={{ gap: 2 }}>
                  <span style={{ fontSize: 14 }}>{p.point}</span>
                  <Source c={p} />
                </div>
              ))}
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

export const Research: React.FC<{ query: string | null; onSearch: (q: string) => void }> = ({ query, onSearch }) => {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<{ message: string; status: number } | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);

  useEffect(() => {
    if (!query) return;
    let cancelled = false;
    setReport(null); setError(null);
    api.research(query)
      .then((r) => { if (!cancelled) { setReport(r); window.scrollTo({ top: 0 }); } })
      .catch((e: ApiError) => { if (!cancelled) setError({ message: e.message, status: e.status }); });
    return () => { cancelled = true; };
  }, [query]);

  const r = report;
  const s = r?.snapshot;
  const cash = r?.cash_quality;

  return (
    <>
      <header className="hero">
        <span className="label"><span className="square" style={{ background: 'var(--series-2)' }} /> Pull · grounded in filings and transcripts</span>
        {r && <h1>{r.name}</h1>}
        <div style={{ marginTop: 8 }}><SearchBox onPick={onSearch} /></div>
        {!query && (
          <div className="row" style={{ marginTop: 4 }}>
            <span className="label faint">Try</span>
            {SUGGESTED.map((t) => <button key={t} className="chip" onClick={() => onSearch(t)}>{t}</button>)}
          </div>
        )}
      </header>

      {query && !r && !error && <><div className="skeleton" style={{ height: 90 }} /><div className="skeleton" style={{ height: 180, marginTop: 12 }} /></>}
      {error && <p className="error">{error.message}</p>}

      {r && s && cash && (
        <>
          <div className="row between" style={{ paddingBottom: 18 }}>
            <div className="stack" style={{ gap: 2 }}>
              <span className="label accent">{r.ticker} · {r.consolidated ? 'consolidated' : 'standalone'}</span>
              {r.price && (
                <span className="row" style={{ gap: 10 }}>
                  <span style={{ fontSize: 22, fontWeight: 300 }} className="mono">₹{num(r.price.close, 2)}</span>
                  <span className={`mono ${tone(r.price.change_pct)}`}>{pct(r.price.change_pct, true, 2)}</span>
                  <span className="label">EOD {r.price.date}</span>
                </span>
              )}
            </div>
            {analysis?.credibility_pct !== undefined && analysis?.credibility_pct !== null && (
              <a href="#promises" onClick={jump('promises')} className="row" style={{ textDecoration: 'none', gap: 10 }}>
                <div className="score-ring" style={{ background: `conic-gradient(var(--accent) ${analysis.credibility_pct * 3.6}deg, var(--surface-2) 0deg)` }}>
                  <div className="score-ring" style={{ width: 54, height: 54, background: 'var(--bg)' }}>{analysis.credibility_pct}%</div>
                </div>
                <div className="stack" style={{ gap: 0 }}>
                  <span className="label accent">Delivery record</span>
                  <span className="label">{analysis.delivered} of {analysis.promises.length} promises</span>
                </div>
              </a>
            )}
          </div>

          <nav className="contents" aria-label="Page contents">
            <span className="label" style={{ marginBottom: 4 }}>Page contents</span>
            {[['business', 'Business'], ['snapshot', 'Financial snapshot'], ['trajectory', 'Trajectory'], ['promises', 'Promises vs delivery'], ['guidance', 'Guidance'], ['bull-bear', 'Bull vs bear'], ['balance', 'Balance sheet'], ['cash', 'Cash quality'], ['documents', 'Primary documents']].map(([id, label]) => (
              <a key={id} href={`#${id}`} onClick={jump(id)}>{label}</a>
            ))}
          </nav>

          <section className="section" id="business">
            <h2>Business</h2>
            <p>{r.about || 'No description available.'}</p>
          </section>

          <section className="section" id="snapshot">
            <h2>Financial snapshot</h2>
            <div className="stats">
              <div className="stat"><span className="label">{r.labels.revenue} TTM</span><span className="value">{crore(s.revenue_ttm_cr)}</span><span className="note">3y CAGR {pct(s.sales_growth['3 Years'], false, 0)}</span></div>
              <div className="stat"><span className="label">{r.is_bank ? 'Fin. margin' : 'EBITDA margin'}</span><span className="value">{pct(s.ebitda_margin_pct, false, 0)}</span><span className="note">latest year</span></div>
              <div className="stat"><span className="label">Net profit TTM</span><span className="value">{crore(s.pat_ttm_cr)}</span><span className="note">3y CAGR {pct(s.profit_growth['3 Years'], false, 0)}</span></div>
              <div className="stat"><span className="label">Market cap</span><span className="value">{crore(s.market_cap_cr)}</span><span className="note">P/E {s.pe ?? '—'}</span></div>
              <div className="stat"><span className="label">ROCE</span><span className="value">{pct(s.roce_pct)}</span><span className="note">return on capital</span></div>
              <div className="stat"><span className="label">ROE</span><span className="value">{pct(s.roe_pct)}</span><span className="note">return on equity</span></div>
              <div className="stat"><span className="label">Debt / equity</span><span className="value">{times(s.debt_to_equity)}</span><span className="note">latest balance sheet</span></div>
              <div className="stat"><span className="label">Sales growth TTM</span><span className="value">{pct(s.sales_growth['TTM'], false, 0)}</span><span className="note">year on year</span></div>
            </div>
          </section>

          <section className="section" id="trajectory">
            <h2>Trajectory</h2>
            <div className="card stack">
              <span className="label accent">{r.labels.revenue}, ₹ Cr by year</span>
              <BarChart ariaLabel={`${r.labels.revenue} by year`} periods={r.trajectory.periods} series={[{ name: r.labels.revenue, color: 'var(--series-1)', values: r.trajectory[r.labels.revenue] as (number | null)[], format: crore }]} />
            </div>
            <div className="card stack">
              <span className="label accent">Net profit, ₹ Cr by year</span>
              <BarChart ariaLabel="Net profit by year" periods={r.trajectory.periods} series={[{ name: 'Net profit', color: 'var(--series-2)', values: r.trajectory['Net Profit'] as (number | null)[], format: crore }]} />
            </div>
            <div className="card stack">
              <span className="label accent">Last 8 quarters</span>
              <table className="table">
                <thead><tr><th>Quarter</th><th className="num">{r.labels.revenue}</th><th className="num">Margin</th><th className="num">Net profit</th></tr></thead>
                <tbody>
                  {r.quarters.periods.map((p, i) => (
                    <tr key={p}>
                      <td className="label">{p}</td>
                      <td className="num mono">{num((r.quarters[r.labels.revenue] as (number | null)[])[i], 0)}</td>
                      <td className="num mono">{pct((r.quarters[r.labels.margin] as (number | null)[])[i], false, 0)}</td>
                      <td className={`num mono ${tone((r.quarters['Net Profit'] as (number | null)[])[i])}`}>{num((r.quarters['Net Profit'] as (number | null)[])[i], 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <AnalysisSection ticker={r.ticker} onResult={setAnalysis} />

          <section className="section" id="balance">
            <h2>Balance sheet</h2>
            <div className="stats">
              <div className="stat"><span className="label">Borrowings</span><span className="value">{crore(r.balance_sheet.borrowings_cr)}</span><span className="note">{r.balance_sheet.period}</span></div>
              <div className="stat"><span className="label">Shareholders' equity</span><span className="value">{crore(r.balance_sheet.equity_cr)}</span><span className="note">capital + reserves</span></div>
              <div className="stat"><span className="label">Debt / equity</span><span className="value">{times(r.balance_sheet.debt_to_equity)}</span><span className="note">{r.is_bank ? 'banks borrow by design' : 'leverage'}</span></div>
              <div className="stat"><span className="label">Working capital</span><span className="value">{num(r.balance_sheet.working_capital_days, 0)}{r.balance_sheet.working_capital_days !== null ? ' d' : ''}</span><span className="note">{r.balance_sheet.cash_conversion_cycle_days !== null ? `cash cycle ${num(r.balance_sheet.cash_conversion_cycle_days, 0)} d` : r.is_bank ? 'not used for banks' : 'not reported'}</span></div>
            </div>
          </section>

          <section className="section" id="cash">
            <h2>Cash quality</h2>
            {r.is_bank ? (
              <p className="notice">For a bank, operating cash flow mostly reflects deposits and loans moving, so comparing it with profit doesn't measure earnings quality.</p>
            ) : (
              <p className="muted" style={{ fontSize: 14 }}>
                Over three years, operating cash flow was {crore(cash.cfo_3y_cr)} against net profit of {crore(cash.pat_3y_cr)}
                {cash.cfo_to_pat_3y !== null && (cash.pat_3y_cr ?? 0) > 0 && <> — <strong style={{ color: 'var(--ink-strong)', fontWeight: 500 }}>{times(cash.cfo_to_pat_3y)}</strong> {cash.cfo_to_pat_3y >= 0.8 ? 'conversion, so profits are turning into cash' : 'conversion, so profits are not fully turning into cash'}</>}.
              </p>
            )}
            <div className="card">
              <BarChart
                ariaLabel="Operating cash flow against net profit by year"
                periods={(cash.history.periods as string[])}
                series={[
                  { name: 'Operating cash flow', color: 'var(--series-1)', values: cash.history['Cash from Operating Activity'] as (number | null)[], format: crore },
                  { name: 'Net profit', color: 'var(--series-2)', values: cash.profit_history, format: crore },
                ]}
              />
            </div>
            <div className="row" style={{ gap: 18 }}>
              <span className="label">Free cash flow (latest) <span className="mono" style={{ color: 'var(--ink-strong)' }}>{crore(cash.free_cash_flow_cr)}</span></span>
              <span className="label">CFO / EBITDA <span className="mono" style={{ color: 'var(--ink-strong)' }}>{pct(cash.cfo_to_ebitda_pct, false, 0)}</span></span>
            </div>
          </section>

          <section className="section" id="documents">
            <h2>Primary documents</h2>
            {(['annual_reports', 'transcripts', 'presentations'] as const).map((k) => (
              <div key={k} className="stack" style={{ gap: 6 }}>
                <span className="label accent">{k === 'annual_reports' ? 'Annual reports' : k === 'transcripts' ? 'Earnings call transcripts' : 'Investor presentations'}</span>
                {r.documents[k].length === 0 ? <span className="muted" style={{ fontSize: 14 }}>None listed.</span> : r.documents[k].map((d) => (
                  <a key={d.url} href={d.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 14 }}>{d.title} ↗</a>
                ))}
              </div>
            ))}
            <p className="label faint">Figures from <a href={r.source_url} target="_blank" rel="noopener noreferrer">screener.in</a>, standardised from company filings</p>
          </section>
        </>
      )}
    </>
  );
};

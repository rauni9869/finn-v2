import React, { useState } from 'react';
import { api, Filing, PeopleBrief } from '../api';
import { ago, CATEGORY_LABELS, crore, pct, tone } from '../format';

export const FilingCard: React.FC<{ filing: Filing; onResearch: (ticker: string) => void }> = ({ filing, onResearch }) => {
  const [people, setPeople] = useState<PeopleBrief | null>(null);
  const [peopleState, setPeopleState] = useState<'idle' | 'loading' | 'error'>('idle');
  const [peopleError, setPeopleError] = useState('');

  const loadPeople = async () => {
    setPeopleState('loading');
    try {
      setPeople(await api.people(filing.id));
      setPeopleState('idle');
    } catch (e) {
      setPeopleError((e as Error).message);
      setPeopleState('error');
    }
  };

  return (
    <article className="card stack" style={{ gap: 10 }}>
      <div className="row between">
        <div className="row" style={{ gap: 10 }}>
          <span className={`square ${filing.priority}`} aria-label={`${filing.priority} priority`} />
          <span className="label accent">{filing.ticker}</span>
          <span className="label">{CATEGORY_LABELS[filing.category] ?? filing.category}</span>
        </div>
        <span className="label faint">{ago(filing.published_at)}</span>
      </div>

      <h3>{filing.summary || filing.title}</h3>
      {filing.summary && <p className="muted" style={{ fontSize: 13 }}>{filing.title}</p>}

      {filing.results && (
        <div className="stack" style={{ gap: 8, marginTop: 4 }}>
          <div className="row between">
            <span className="label">{filing.results.quarter} first cut · {filing.results.consolidated ? 'consolidated' : 'standalone'}</span>
            {filing.results.margin_pct !== null && (
              <span className="label">
                Margin {pct(filing.results.margin_pct, false, 0)}
                {filing.results.margin_yoy_bps !== null && <span className={tone(filing.results.margin_yoy_bps)}> {filing.results.margin_yoy_bps > 0 ? '+' : ''}{filing.results.margin_yoy_bps} bps YoY</span>}
              </span>
            )}
          </div>
          <table className="table">
            <thead>
              <tr><th></th><th className="num">₹ Cr</th><th className="num">QoQ</th><th className="num">YoY</th></tr>
            </thead>
            <tbody>
              {filing.results.metrics.map((m) => (
                <tr key={m.key}>
                  <td className="label accent">{m.label}</td>
                  <td className="num mono">{crore(m.value_cr).replace('₹', '').replace(' Cr', '')}</td>
                  <td className={`num mono ${tone(m.qoq_pct)}`}>{pct(m.qoq_pct, true)}</td>
                  <td className={`num mono ${tone(m.yoy_pct)}`}>{pct(m.yoy_pct, true)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {filing.category === 'management_change' && (
        <div className="stack" style={{ gap: 8 }}>
          {peopleState === 'idle' && !people && (
            <button className="chip" style={{ justifySelf: 'start' }} onClick={loadPeople}>Who is this?</button>
          )}
          {peopleState === 'loading' && <div className="row muted" style={{ fontSize: 13 }}><span className="spinner" /> Looking up the people involved…</div>}
          {peopleState === 'error' && <p className="error" style={{ fontSize: 13 }}>{peopleError} <button className="label" onClick={loadPeople}>Retry</button></p>}
          {people && (
            <div className="stack" style={{ gap: 10, borderTop: '1px solid var(--line-faint)', paddingTop: 10 }}>
              {people.people.map((p) => (
                <div key={p.name} className="stack" style={{ gap: 4 }}>
                  <div className="row"><strong style={{ fontWeight: 500 }}>{p.name}</strong><span className="label">{p.change} · {p.role}</span></div>
                  {p.known && p.background.length ? (
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }} className="muted">
                      {p.background.map((b) => <li key={b}>{b}</li>)}
                    </ul>
                  ) : <p className="faint" style={{ fontSize: 13 }}>No reliable background found.</p>}
                </div>
              ))}
              {people.why_it_matters && <p style={{ fontSize: 13 }}>{people.why_it_matters}</p>}
              {people.sources.length > 0 && (
                <div className="row" style={{ gap: 12 }}>
                  <span className="label faint">Sources</span>
                  {people.sources.map((s) => <a key={s.url} className="label" href={s.url} target="_blank" rel="noopener noreferrer">{s.title} ↗</a>)}
                </div>
              )}
              <p className="label faint">{people.searched ? "AI summary of a web search · check the sources before acting" : "From the AI model's general knowledge, without a web search · may be out of date or wrong"}</p>
            </div>
          )}
        </div>
      )}

      <div className="row" style={{ gap: 16, marginTop: 2 }}>
        <a className="label" href={filing.url} target="_blank" rel="noopener noreferrer">BSE filing ↗</a>
        <button className="label" onClick={() => onResearch(filing.ticker)}>Research {filing.ticker} →</button>
      </div>
    </article>
  );
};

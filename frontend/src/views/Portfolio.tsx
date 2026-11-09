import React, { useEffect, useState } from 'react';
import { api, Stock } from '../api';
import { Sparkline } from '../components/BarChart';
import { num, pct, tone } from '../format';

export const Portfolio: React.FC<{ onResearch: (ticker: string) => void }> = ({ onResearch }) => {
  const [stocks, setStocks] = useState<Stock[] | null>(null);
  const [error, setError] = useState('');
  const [sort, setSort] = useState<'move' | 'volume' | 'name'>('move');

  useEffect(() => {
    api.portfolio().then((r) => setStocks(r.stocks)).catch((e) => setError((e as Error).message));
  }, []);

  const sorted = [...(stocks ?? [])].sort((a, b) => {
    if (sort === 'name') return a.ticker.localeCompare(b.ticker);
    if (sort === 'volume') return (b.eod?.volume_multiple ?? -1) - (a.eod?.volume_multiple ?? -1);
    return Math.abs(b.eod?.change_pct ?? 0) - Math.abs(a.eod?.change_pct ?? 0);
  });
  const date = stocks?.find((s) => s.eod)?.eod?.date;

  return (
    <>
      <header className="hero">
        <span className="label"><span className="square" style={{ background: 'var(--series-1)' }} /> Portfolio · end of day{date ? ` ${date}` : ''}</span>
        <div className="pills" style={{ marginTop: 8, justifySelf: 'start' }} role="tablist" aria-label="Sort by">
          {([['move', 'Biggest move'], ['volume', 'Volume'], ['name', 'A–Z']] as const).map(([k, l]) => (
            <button key={k} role="tab" aria-selected={sort === k} className={`pill ${sort === k ? 'active' : ''}`} onClick={() => setSort(k)}>{l}</button>
          ))}
        </div>
      </header>
      {error && <p className="error">{error}</p>}
      {!stocks && !error && <div className="skeleton" style={{ height: 320 }} />}
      {stocks && (
        <table className="table">
          <thead>
            <tr><th>Company</th><th className="num">Close</th><th className="num">Day</th><th className="num hide-sm">Vol / 20d</th><th className="hide-sm" aria-label="30-day trend"></th></tr>
          </thead>
          <tbody>
            {sorted.map((s) => (
              <tr key={s.ticker} className="click" onClick={() => onResearch(s.ticker)} tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && onResearch(s.ticker)}>
                <td>
                  <div className="label accent">{s.ticker}</div>
                  <div className="muted" style={{ fontSize: 13 }}>{s.name} · {s.sector}</div>
                </td>
                <td className="num mono">{s.eod ? num(s.eod.close, 2) : 'n/a'}</td>
                <td className={`num mono ${tone(s.eod?.change_pct)}`}>{pct(s.eod?.change_pct, true, 2)}</td>
                <td className={`num mono hide-sm ${(s.eod?.volume_multiple ?? 0) >= 2 ? '' : 'muted'}`} style={(s.eod?.volume_multiple ?? 0) >= 2 ? { color: 'var(--accent)' } : undefined}>
                  {s.eod?.volume_multiple != null ? `${s.eod.volume_multiple.toFixed(2)}x` : '—'}
                </td>
                <td className="hide-sm" style={{ textAlign: 'right' }}><Sparkline values={s.eod?.closes} up={(s.eod?.closes?.[s.eod.closes.length - 1] ?? 0) >= (s.eod?.closes?.[0] ?? 0)} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="label faint" style={{ marginTop: 12 }}>Prices from Yahoo Finance · last completed session</p>
    </>
  );
};

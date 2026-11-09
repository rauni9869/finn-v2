import React, { useEffect, useState } from 'react';
import { Portfolio } from './views/Portfolio';
import { Research } from './views/Research';
import { Today } from './views/Today';

type Route = { view: 'today' | 'research' | 'portfolio'; query: string | null };

function parseHash(): Route {
  const [, view, query] = window.location.hash.split('/');
  if (view === 'research') return { view, query: query ? decodeURIComponent(query) : null };
  if (view === 'portfolio') return { view, query: null };
  return { view: 'today', query: null };
}

const TABS = [['today', 'Today'], ['research', 'Research'], ['portfolio', 'Portfolio']] as const;

export const App: React.FC = () => {
  const [route, setRoute] = useState<Route>(parseHash);
  // Pages visited inside FINN, so Back returns to the previous one and never leaves the app
  const [trail, setTrail] = useState<string[]>(() => [window.location.hash || '#/today']);

  useEffect(() => {
    const onHash = () => {
      setRoute(parseHash());
      const hash = window.location.hash || '#/today';
      setTrail((t) => {
        if (t[t.length - 1] === hash) return t;
        // Arriving at the page before this one means the user went back
        if (t.length > 1 && t[t.length - 2] === hash) return t.slice(0, -1);
        return [...t, hash];
      });
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const canGoBack = trail.length > 1;
  const goBack = () => {
    if (canGoBack) window.history.back();
    else window.location.hash = '/today';
  };

  const research = (q: string) => {
    window.location.hash = `/research/${encodeURIComponent(q)}`;
    window.scrollTo({ top: 0 });
  };

  return (
    <>
      <div className="topbar">
        <div className="topbar-inner">
          <div className="row" style={{ gap: 10, flexWrap: 'nowrap' }}>
            {/* Lives in the sticky header so it stays reachable anywhere on a long page */}
            {route.view !== 'today' && (
              <button className="back-btn" onClick={goBack} aria-label={canGoBack ? 'Go back' : 'Go to Today'} title={canGoBack ? 'Back' : 'Today'}>
                ←
              </button>
            )}
          <a href="#/today" className={`brand ${route.view !== 'today' ? 'brand-compact' : ''}`} style={{ textDecoration: 'none' }} aria-label="FINN home">
            <span className="brand-grid" aria-hidden="true">
              <span style={{ background: 'var(--accent)' }} /><span style={{ background: 'var(--series-2)' }} />
              <span style={{ background: 'var(--down)' }} /><span style={{ background: 'var(--up)' }} />
            </span>
            <span className="brand-name">FINN</span>
          </a>
          </div>
          <nav className="pills" aria-label="Sections">
            {TABS.map(([v, label]) => (
              <a key={v} href={`#/${v}${v === 'research' && route.query ? `/${encodeURIComponent(route.query)}` : ''}`} className={`pill ${route.view === v ? 'active' : ''}`} style={{ textDecoration: 'none' }} aria-current={route.view === v ? 'page' : undefined}>{label}</a>
            ))}
          </nav>
        </div>
      </div>
      <main className="page">
        {route.view === 'today' && <Today onResearch={research} />}
        {route.view === 'research' && <Research query={route.query} onSearch={research} />}
        {route.view === 'portfolio' && <Portfolio onResearch={research} />}
      </main>
    </>
  );
};

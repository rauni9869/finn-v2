import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, AlertSettings, api, Digest } from '../api';
import { FilingCard } from '../components/FilingCard';
import { CATEGORY_LABELS, pct } from '../format';

const WINDOWS = [{ label: '24h', hours: 24 }, { label: '48h', hours: 48 }, { label: '7 days', hours: 168 }];
const MATERIAL = ['results', 'M&A', 'management_change', 'fund_raise', 'litigation', 'capex', 'credit_rating', 'pledging', 'insider_trading', 'dividend'];
const DEFAULT_SETTINGS: AlertSettings = {
  volume_multiple: 2,
  price_move_pct: 4,
  categories: ['results', 'M&A', 'management_change', 'fund_raise', 'litigation', 'capex'],
  filing_window_hours: 24,
};

function loadSettings(): AlertSettings {
  try {
    const saved = localStorage.getItem('finn.alerts');
    return saved ? { ...DEFAULT_SETTINGS, ...JSON.parse(saved) } : DEFAULT_SETTINGS;
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function speak(text: string) {
  if (!('speechSynthesis' in window)) return false;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.05;
  window.speechSynthesis.speak(u);
  return true;
}

export const Today: React.FC<{ onResearch: (ticker: string) => void }> = ({ onResearch }) => {
  const [hours, setHours] = useState(24);
  const [digest, setDigest] = useState<Digest | null>(null);
  const [digestError, setDigestError] = useState('');
  const [settings, setSettings] = useState<AlertSettings>(loadSettings);
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [alertsError, setAlertsError] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [showRoutine, setShowRoutine] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const latestAlerts = useRef(0);

  const loadDigest = useCallback(async (h: number) => {
    setDigestError('');
    try {
      setDigest(await api.digest(h));
    } catch (e) {
      setDigestError((e as Error).message);
    }
  }, []);

  useEffect(() => { loadDigest(hours); }, [hours, loadDigest]);

  useEffect(() => {
    try { localStorage.setItem('finn.alerts', JSON.stringify(settings)); } catch { /* storage unavailable */ }
    const id = ++latestAlerts.current;
    const timer = setTimeout(async () => {
      try {
        const res = await api.alerts(settings);
        if (id === latestAlerts.current) { setAlerts(res.alerts); setAlertsError(''); }
      } catch (e) {
        if (id === latestAlerts.current) setAlertsError((e as Error).message);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [settings]);

  const brief = () => {
    if (speaking) { window.speechSynthesis.cancel(); setSpeaking(false); return; }
    const lines = ['Here is your FINN briefing.'];
    const market = (alerts ?? []).filter((a) => a.kind === 'market');
    if (market.length) lines.push(`${market.length} unusual market ${market.length === 1 ? 'move' : 'moves'}.`, ...market.slice(0, 3).map((a) => `${a.company}: ${a.headline}.`));
    const top = digest?.material.filter((f) => f.priority === 'HIGH').slice(0, 4) ?? [];
    if (top.length) lines.push('Top filings.', ...top.map((f) => `${f.company}: ${f.summary || f.title}.`));
    if (!market.length && !top.length) lines.push('Nothing material in this window.');
    if (speak(lines.join(' '))) {
      setSpeaking(true);
      const check = setInterval(() => { if (!window.speechSynthesis.speaking) { setSpeaking(false); clearInterval(check); } }, 500);
    }
  };

  const toggleCategory = (c: string) =>
    setSettings((s) => ({ ...s, categories: s.categories.includes(c) ? s.categories.filter((x) => x !== c) : [...s.categories, c] }));

  const marketAlerts = alerts?.filter((a) => a.kind === 'market') ?? [];
  const filingAlerts = alerts?.filter((a) => a.kind === 'filing') ?? [];

  return (
    <>
      <header className="hero">
        <span className="label"><span className="square" /> Push · live from BSE via screener.in</span>
        <div className="row" style={{ marginTop: 8, gap: 10 }}>
          <div className="pills" role="tablist" aria-label="Time window">
            {WINDOWS.map((w) => (
              <button key={w.hours} role="tab" aria-selected={hours === w.hours} className={`pill ${hours === w.hours ? 'active' : ''}`} onClick={() => setHours(w.hours)}>{w.label}</button>
            ))}
          </div>
          <button className="btn" onClick={brief}>{speaking ? '■ Stop' : '▶ Brief me'}</button>
        </div>
      </header>

      <section className="section" id="alerts">
        <div className="section-head">
          <h2>Alerts</h2>
          <button className="label" onClick={() => setShowSettings(true)}>
            Vol ≥ {settings.volume_multiple.toFixed(1)}x · Move ≥ ±{settings.price_move_pct.toFixed(1)}% · Edit
          </button>
        </div>
        {alertsError && <p className="error">{alertsError}</p>}
        {!alerts && !alertsError && <div className="skeleton" style={{ height: 64 }} />}
        {alerts && !alerts.length && <p className="muted">Nothing crossed your thresholds. Lower them to see more.</p>}
        <div className="stack">
          {marketAlerts.map((a) => (
            <button key={`m-${a.ticker}`} className="card interactive row between" style={{ textAlign: 'left' }} onClick={() => onResearch(a.ticker)}>
              <div className="stack" style={{ gap: 2 }}>
                <span className="row"><span className="square" /><span className="label accent">{a.ticker}</span><span className="label">EOD {a.at}</span></span>
                <span>{a.headline}</span>
              </div>
              <span className={`mono ${a.eod && a.eod.change_pct >= 0 ? 'up' : 'down'}`}>{pct(a.eod?.change_pct, true, 2)}</span>
            </button>
          ))}
          {filingAlerts.map((a) => (
            <div key={`f-${a.filing_id}`} className="row" style={{ padding: '4px 2px', gap: 10 }}>
              <span className="square HIGH" />
              <span className="label accent">{a.ticker}</span>
              <span style={{ fontSize: 14 }}>{CATEGORY_LABELS[a.category ?? ''] ?? a.category}: {a.headline}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="section" id="filings">
        <div className="section-head">
          <h2>Filings</h2>
          {digest && <span className="label">{digest.material.length} material · {digest.routine.length} routine</span>}
        </div>
        {digestError && <p className="error">{digestError} <button className="label" onClick={() => loadDigest(hours)}>Retry</button></p>}
        {!digest && !digestError && <><div className="skeleton" style={{ height: 120 }} /><div className="skeleton" style={{ height: 120 }} /></>}
        {digest && !digest.material.length && <p className="muted">No material filings in this window.</p>}
        <div className="stack">
          {digest?.material.map((f) => <FilingCard key={f.id} filing={f} onResearch={onResearch} />)}
        </div>
        {digest && digest.routine.length > 0 && (
          <div className="stack" style={{ gap: 0 }}>
            <button className="row between label" style={{ padding: '10px 0' }} onClick={() => setShowRoutine(!showRoutine)} aria-expanded={showRoutine}>
              <span className="row"><span className="square LOW" /> {digest.routine.length} routine filings collapsed</span>
              <span>{showRoutine ? 'Hide' : 'Show'}</span>
            </button>
            {showRoutine && digest.routine.map((f) => (
              <a key={f.id} href={f.url} target="_blank" rel="noopener noreferrer" className="row" style={{ padding: '8px 0', borderTop: '1px solid var(--line-faint)', textDecoration: 'none', gap: 10 }}>
                <span className="label" style={{ minWidth: 86 }}>{f.ticker}</span>
                <span className="muted" style={{ fontSize: 13, flex: 1 }}>{f.title}</span>
              </a>
            ))}
          </div>
        )}
        <p className="label faint">Latest 5 announcements per company · summaries by screener.in · priority by FINN</p>
      </section>

      {showSettings && (
        <div className="sheet-backdrop" onClick={() => setShowSettings(false)}>
          <div className="sheet" role="dialog" aria-label="Alert settings" onClick={(e) => e.stopPropagation()}>
            <div className="row between"><h2>Alert thresholds</h2><button className="label" onClick={() => setShowSettings(false)}>Done</button></div>
            <p className="muted" style={{ fontSize: 14 }}>You decide what counts as unusual. {marketAlerts.length} market {marketAlerts.length === 1 ? 'alert' : 'alerts'} at these settings.</p>
            <label className="stack" style={{ gap: 6 }}>
              <span className="row between"><span className="label accent">Volume vs 20-day average</span><span className="mono">≥ {settings.volume_multiple.toFixed(1)}x</span></span>
              <input type="range" min={1} max={6} step={0.1} value={settings.volume_multiple} onChange={(e) => setSettings({ ...settings, volume_multiple: Number(e.target.value) })} />
            </label>
            <label className="stack" style={{ gap: 6 }}>
              <span className="row between"><span className="label accent">Price move in a day</span><span className="mono">≥ ±{settings.price_move_pct.toFixed(1)}%</span></span>
              <input type="range" min={0.5} max={10} step={0.5} value={settings.price_move_pct} onChange={(e) => setSettings({ ...settings, price_move_pct: Number(e.target.value) })} />
            </label>
            <div className="stack" style={{ gap: 8 }}>
              <span className="label accent">Alert me on these filings (last 24h)</span>
              <div className="row">
                {MATERIAL.map((c) => (
                  <button key={c} className={`chip ${settings.categories.includes(c) ? 'on' : ''}`} aria-pressed={settings.categories.includes(c)} onClick={() => toggleCategory(c)}>{CATEGORY_LABELS[c]}</button>
                ))}
              </div>
            </div>
            <button className="label" style={{ justifySelf: 'start' }} onClick={() => setSettings(DEFAULT_SETTINGS)}>Reset to defaults</button>
          </div>
        </div>
      )}
    </>
  );
};

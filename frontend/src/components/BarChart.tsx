import React, { useState } from 'react';

export interface BarSeries {
  name: string;
  color: string;
  values: (number | null)[];
  format: (v: number | null) => string;
}

interface Props {
  periods: string[];
  series: BarSeries[];
  height?: number;
  ariaLabel: string;
}

// Grouped bars from a zero baseline, with a hover tooltip per period
export const BarChart: React.FC<Props> = ({ periods, series, height = 160, ariaLabel }) => {
  const [hover, setHover] = useState<number | null>(null);
  const width = 640;
  const pad = { top: 14, bottom: 4, left: 4, right: 4 };
  const all = series.flatMap((s) => s.values.filter((v): v is number => v !== null));
  if (!all.length) return <p className="muted">No data reported.</p>;
  const max = Math.max(0, ...all);
  const min = Math.min(0, ...all);
  const span = max - min || 1;
  const plotH = height - pad.top - pad.bottom;
  const y = (v: number) => pad.top + ((max - v) / span) * plotH;
  const zero = y(0);
  const groupW = (width - pad.left - pad.right) / periods.length;
  const gap = 2;
  const barW = Math.min(28, (groupW * 0.62 - gap * (series.length - 1)) / series.length);
  const groupInner = barW * series.length + gap * (series.length - 1);

  return (
    <div style={{ position: 'relative' }}>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" role="img" aria-label={ariaLabel} style={{ display: 'block', overflow: 'visible' }}>
        <line x1={pad.left} x2={width - pad.right} y1={zero} y2={zero} stroke="var(--line)" strokeWidth={1} />
        {periods.map((p, i) => {
          const gx = pad.left + i * groupW + (groupW - groupInner) / 2;
          return (
            <g key={p}>
              {series.map((s, k) => {
                const v = s.values[i];
                if (v === null || v === undefined) return null;
                const top = Math.min(y(v), zero);
                const h = Math.max(Math.abs(y(v) - zero), 1);
                const r = Math.min(4, barW / 2, h);
                const x = gx + k * (barW + gap);
                // Round only the end away from the baseline
                const d = v >= 0
                  ? `M${x},${top + h} V${top + r} Q${x},${top} ${x + r},${top} H${x + barW - r} Q${x + barW},${top} ${x + barW},${top + r} V${top + h} Z`
                  : `M${x},${top} V${top + h - r} Q${x},${top + h} ${x + r},${top + h} H${x + barW - r} Q${x + barW},${top + h} ${x + barW},${top + h - r} V${top} Z`;
                return <path key={s.name} d={d} fill={s.color} opacity={hover === null || hover === i ? 1 : 0.45} />;
              })}
              <rect
                x={pad.left + i * groupW} y={0} width={groupW} height={height} fill="transparent"
                onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
                onClick={() => setHover(hover === i ? null : i)}
              />
            </g>
          );
        })}
      </svg>
      {/* Period labels as HTML so they stay readable when the chart scales down */}
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${periods.length}, 1fr)`, marginTop: 6 }}>
        {periods.map((p) => (
          <span key={p} className="label faint" style={{ textAlign: 'center', fontSize: 10 }}>{p.replace(/^([A-Za-z]{3}) \d{2}(\d{2})$/, "$1 '$2")}</span>
        ))}
      </div>
      {hover !== null && (
        <div className="chart-tip" style={{ left: `${((pad.left + hover * groupW + groupW / 2) / width) * 100}%`, top: 0 }}>
          <div className="label">{periods[hover]}</div>
          {series.map((s) => (
            <div key={s.name} className="row" style={{ gap: 6 }}>
              <span className="swatch" style={{ background: s.color }} />
              <span className="muted">{s.name}</span>
              <span className="mono">{s.format(s.values[hover] ?? null)}</span>
            </div>
          ))}
        </div>
      )}
      {series.length > 1 && (
        <div className="legend" style={{ marginTop: 8 }}>
          {series.map((s) => (
            <span key={s.name}><span className="swatch" style={{ background: s.color }} />{s.name}</span>
          ))}
        </div>
      )}
    </div>
  );
};

export const Sparkline: React.FC<{ values?: number[]; up: boolean }> = ({ values, up }) => {
  if (!values || values.length < 2) return null;
  const w = 72, h = 22;
  const min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
  const points = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - 2 - ((v - min) / span) * (h - 4)}`).join(' ');
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
      <polyline points={points} fill="none" stroke={up ? 'var(--up)' : 'var(--down)'} strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  );
};

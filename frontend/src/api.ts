// Same origin: Vite proxies /api in development, and FastAPI serves the built app in production.
const BASE: string = import.meta.env.VITE_API_URL ?? '';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError('Could not reach the FINN server. Check your connection and try again.', 0);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    // No detail means the request never reached FINN's backend, usually because it is still starting
    const fallback = res.status >= 500
      ? 'The FINN server is not responding. It may still be starting, so try again in a moment.'
      : `Request failed (HTTP ${res.status})`;
    throw new ApiError(body?.detail || fallback, res.status);
  }
  return body as T;
}

export interface Eod {
  date: string;
  close: number;
  change_pct: number;
  volume: number;
  avg_volume_20d: number;
  volume_multiple: number | null;
  closes?: number[];
}

export interface Stock {
  ticker: string;
  name: string;
  sector: string;
  size: string;
  eod: Eod | null;
}

export interface ResultsMetric {
  key: string;
  label: string;
  value_cr: number | null;
  qoq_pct: number | null;
  yoy_pct: number | null;
}

export interface Filing {
  id: string;
  ticker: string;
  company: string;
  published_at: string;
  title: string;
  summary: string;
  url: string;
  category: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  classified_by: string;
  people?: PeopleBrief | null;
  results: {
    quarter: string;
    metrics: ResultsMetric[];
    margin_pct: number | null;
    margin_yoy_bps: number | null;
    consolidated: boolean;
    source: string;
  } | null;
}

export interface Digest {
  window_hours: number;
  generated_at: string;
  counts: Record<string, number>;
  material: Filing[];
  routine: Filing[];
}

export interface AlertSettings {
  volume_multiple: number;
  price_move_pct: number;
  categories: string[];
  filing_window_hours: number;
}

export interface Alert {
  kind: 'market' | 'filing';
  ticker: string;
  company: string;
  headline: string;
  at: string;
  eod?: Eod;
  filing_id?: string;
  category?: string;
}

export interface PeopleBrief {
  people: { name: string; role: string; change: string; known: boolean; background: string[] }[];
  why_it_matters: string;
  sources: { title: string; url: string }[];
  searched: boolean;
}

export type Series = { periods: string[] } & Record<string, (number | null)[] | string[]>;

export interface DocLink { title: string; url: string; period?: string }

export interface Report {
  ticker: string;
  name: string;
  about: string;
  source_url: string;
  consolidated: boolean;
  is_bank: boolean;
  price: Eod | null;
  snapshot: {
    market_cap_cr: number | null;
    pe: number | null;
    roce_pct: number | null;
    roe_pct: number | null;
    revenue_ttm_cr: number | null;
    ebitda_margin_pct: number | null;
    pat_ttm_cr: number | null;
    debt_to_equity: number | null;
    sales_growth: Record<string, number | null>;
    profit_growth: Record<string, number | null>;
  };
  trajectory: Series;
  quarters: Series;
  labels: { revenue: string; margin: string; ebitda: string };
  balance_sheet: {
    period: string | null;
    borrowings_cr: number | null;
    equity_cr: number | null;
    debt_to_equity: number | null;
    working_capital_days: number | null;
    cash_conversion_cycle_days: number | null;
  };
  cash_quality: {
    cfo_3y_cr: number | null;
    pat_3y_cr: number | null;
    cfo_to_pat_3y: number | null;
    free_cash_flow_cr: number | null;
    cfo_to_ebitda_pct: number | null;
    history: Series;
    profit_history: (number | null)[];
  };
  documents: { annual_reports: DocLink[]; transcripts: DocLink[]; presentations: DocLink[] };
}

export interface Cited { transcript: string; page: number | null; quote: string; url: string | null }

export interface Analysis {
  ticker: string;
  summary: string;
  coverage: string;
  transcripts_read: { label: string; url: string; pages: number }[];
  promises: (Cited & { promised: string; actual_delivered: string; verdict: string; reasoning: string })[];
  delivered: number;
  credibility_pct: number | null;
  guidance: (Cited & { topic: string; target: string })[];
  bull: (Cited & { point: string })[];
  bear: (Cited & { point: string })[];
  dropped_unverified: number;
}

export const api = {
  portfolio: () => request<{ stocks: Stock[]; ad_hoc: string[] }>('/api/portfolio'),
  digest: (hours: number) => request<Digest>(`/api/digest?window_hours=${hours}`),
  alerts: (settings: AlertSettings) =>
    request<{ alerts: Alert[] }>('/api/alerts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    }),
  people: (id: string) => request<PeopleBrief>(`/api/filings/${id}/people`),
  search: (q: string) => request<{ results: { ticker: string; name: string }[] }>(`/api/search?q=${encodeURIComponent(q)}`),
  research: (q: string) => request<Report>(`/api/research/${encodeURIComponent(q)}`),
  analysis: (q: string) => request<Analysis>(`/api/research/${encodeURIComponent(q)}/analysis`),
};

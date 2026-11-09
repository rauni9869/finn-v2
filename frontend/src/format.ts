export const CATEGORY_LABELS: Record<string, string> = {
  results: 'Results',
  'M&A': 'M&A',
  fund_raise: 'Fund raise',
  management_change: 'Management',
  litigation: 'Litigation',
  insider_trading: 'Insider trade',
  earnings_call: 'Earnings call',
  investor_meetings: 'Investor meet',
  credit_rating: 'Credit rating',
  dividend: 'Dividend',
  bonus_split: 'Bonus / split',
  capex: 'Capex',
  press_release: 'Press release',
  postal_ballot: 'Postal ballot',
  agm_egm: 'AGM / EGM',
  pledging: 'Pledging',
  unclassified: 'Routine',
};

export function crore(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  const abs = Math.abs(value);
  if (abs >= 100000) return `₹${(value / 100000).toFixed(2)} L Cr`;
  return `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })} Cr`;
}

export function pct(value: number | null | undefined, signed = false, digits = 1): string {
  if (value === null || value === undefined) return '—';
  const sign = signed && value > 0 ? '+' : '';
  return `${sign}${value.toFixed(digits)}%`;
}

export function times(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return '—';
  return `${value.toFixed(digits)}x`;
}

export function num(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return '—';
  return value.toLocaleString('en-IN', { maximumFractionDigits: digits });
}

export function tone(value: number | null | undefined): string {
  if (value === null || value === undefined || value === 0) return '';
  return value > 0 ? 'up' : 'down';
}

export function ago(iso: string): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 60) return `${Math.max(minutes, 1)}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours}h ago`;
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

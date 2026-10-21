export type Exchange = 'NSE' | 'BSE'
export type Horizon = 'short' | 'long'
export type Signal = 'buy' | 'hold' | 'sell'
export type SectorCall = 'overweight' | 'neutral' | 'underweight'

export interface Ticker {
  id: number
  exchange: Exchange
  symbol: string
  name: string
  sector: string
  tag: 'holding' | 'watching'
  quantity: number | null
  avg_price: number | null
  target: number | null
  stop_loss: number | null
  horizon_override: Horizon | null
}

export interface Quote {
  price: number | null
  prev_close: number | null
  ch1m: number | null
  ch3m: number | null
  ch1y: number | null
  high52: number | null
  low52: number | null
  pe: number | null
  market_cap: number | null
  dividend_yield: number | null
  source: string
  updated_at: string
}

export interface Analysis {
  score: number | null
  signal: Signal | null
  horizon: Horizon
  horizon_suggested: Horizon
  components: Record<'upside' | 'momentum' | 'valuation' | 'risk', number | null>
  reasons: string[]
}

export interface TickerRow {
  ticker: Ticker
  quote: Quote | null
  analysis: Analysis
  invested: number | null
  value: number | null
  pnl: number | null
}

export interface SectorRow {
  sector: string
  count: number
  score: number | null
  call: SectorCall | null
  avg_pe: number | null
  avg_ch1m: number | null
  invested: number | null
  value: number | null
  pnl: number | null
  signals: Record<Signal, number>
}

export interface Overview {
  tickers: TickerRow[]
  sectors: SectorRow[]
}

export type TickerInput = Omit<Ticker, 'id'>

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // keep the generic message
    }
    throw new Error(detail)
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

export const api = {
  overview: () => call<Overview>('/api/overview'),
  addTicker: (t: TickerInput) => call<Ticker>('/api/tickers', { method: 'POST', body: JSON.stringify(t) }),
  updateTicker: (id: number, t: Partial<TickerInput>) =>
    call<Ticker>(`/api/tickers/${id}`, { method: 'PATCH', body: JSON.stringify(t) }),
  deleteTicker: (id: number) => call<void>(`/api/tickers/${id}`, { method: 'DELETE' }),
  refresh: () => call<{ updated: number; failed: string[]; source: string }>('/api/refresh', { method: 'POST' }),
  kiteStatus: () => call<{ configured: boolean; logged_in: boolean }>('/api/kite/status'),
  importHoldings: () => call<{ added: number; updated: number }>('/api/kite/import-holdings', { method: 'POST' }),
}

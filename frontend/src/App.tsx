import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, type Overview, type SectorRow, type Ticker, type TickerInput, type TickerRow } from './api'
import { CALL_LABEL, SIGNAL_LABEL, lakhCrore, money, num, pct, tone } from './format'
import TickerForm from './TickerForm'

type SortKey = 'symbol' | 'sector' | 'price' | 'score' | 'ch1m' | 'pe' | 'pnl'

export default function App() {
  const [data, setData] = useState<Overview | null>(null)
  const [kite, setKite] = useState<{ configured: boolean; logged_in: boolean } | null>(null)
  const [status, setStatus] = useState('Loading…')
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState<Ticker | null>(null)
  const [confirmId, setConfirmId] = useState<number | null>(null)
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: 'score', dir: -1 })

  const load = useCallback(async () => {
    try {
      const [ov, ks] = await Promise.all([api.overview(), api.kiteStatus()])
      setData(ov)
      setKite(ks)
      setStatus(`${ov.tickers.length} tickers`)
    } catch (e) {
      setStatus('Could not reach the backend. Is it running on port 8000?')
      console.error(e)
    }
  }, [])

  useEffect(() => {
    const kiteParam = new URLSearchParams(location.search).get('kite')
    if (kiteParam) history.replaceState(null, '', '/')
    load().then(() => {
      if (kiteParam === 'connected') setStatus('Connected to Kite.')
      if (kiteParam === 'failed') setStatus('Kite login did not complete. Try again.')
    })
  }, [load])

  async function run(label: string, fn: () => Promise<string>) {
    setBusy(true)
    setStatus(label)
    try {
      setStatus(await fn())
      await load()
    } catch (e) {
      setStatus((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const refresh = () =>
    run('Refreshing prices…', async () => {
      const r = await api.refresh()
      const src = r.source === 'kite' ? 'Kite' : 'Yahoo Finance'
      return `Updated ${r.updated} from ${src}` + (r.failed.length ? `. No data for ${r.failed.join(', ')}.` : '.')
    })

  const importHoldings = () =>
    run('Importing holdings…', async () => {
      const r = await api.importHoldings()
      return `Imported holdings: ${r.added} added, ${r.updated} updated. Refresh to get prices.`
    })

  async function save(t: TickerInput, id?: number) {
    if (id) await api.updateTicker(id, t)
    else await api.addTicker(t)
    setEditing(null)
    await load()
  }

  async function remove(id: number) {
    setConfirmId(null)
    try {
      await api.deleteTicker(id)
      await load()
    } catch (e) {
      setStatus((e as Error).message)
    }
  }

  const sectorNames = useMemo(() => [...new Set((data?.tickers ?? []).map((r) => r.ticker.sector).filter(Boolean))].sort(), [data])

  const rows = useMemo(() => {
    const val = (r: TickerRow): string | number | null => {
      switch (sort.key) {
        case 'symbol': return r.ticker.symbol
        case 'sector': return r.ticker.sector
        case 'price': return r.quote?.price ?? null
        case 'score': return r.analysis.score
        case 'ch1m': return r.quote?.ch1m ?? null
        case 'pe': return r.quote?.pe ?? null
        case 'pnl': return r.pnl
      }
    }
    return [...(data?.tickers ?? [])].sort((a, b) => {
      const va = val(a), vb = val(b)
      if (va == null && vb == null) return a.ticker.symbol.localeCompare(b.ticker.symbol)
      if (va == null) return 1
      if (vb == null) return -1
      const c = typeof va === 'string' ? va.localeCompare(vb as string) : (va as number) - (vb as number)
      return c * sort.dir
    })
  }, [data, sort])

  const totals = useMemo(() => {
    const t = data?.tickers ?? []
    const invested = t.reduce((s, r) => s + (r.invested ?? 0), 0)
    const value = t.reduce((s, r) => s + (r.value ?? 0), 0)
    const counts = { buy: 0, hold: 0, sell: 0 }
    t.forEach((r) => r.analysis.signal && counts[r.analysis.signal]++)
    return { invested, value, pnl: value - invested, counts }
  }, [data])

  const th = (key: SortKey, label: string) => (
    <th
      onClick={() => setSort((s) => ({ key, dir: s.key === key ? (s.dir === 1 ? -1 : 1) : key === 'symbol' || key === 'sector' ? 1 : -1 }))}
      aria-sort={sort.key === key ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none'}
    >
      {label}
      {sort.key === key ? (sort.dir === 1 ? ' ↑' : ' ↓') : ''}
    </th>
  )

  return (
    <div className="wrap">
      <header>
        <div>
          <div className="label">NSE · BSE</div>
          <h1>Sector Watchlist</h1>
          <p className="status" role="status">{status}</p>
        </div>
        <div className="actions">
          {kite?.configured && !kite.logged_in && (
            <a className="btn" href="/api/kite/login">Log in to Kite</a>
          )}
          {kite?.logged_in && (
            <button onClick={importHoldings} disabled={busy}>Import Kite holdings</button>
          )}
          <button className="primary" onClick={refresh} disabled={busy}>Refresh prices</button>
        </div>
      </header>

      <section className="strip" aria-label="Summary">
        <div><span className="label">Tickers</span><span className="v">{data?.tickers.length ?? '—'}</span><span className="s">{data?.sectors.length ?? 0} sectors</span></div>
        <div><span className="label">Signals</span><span className="v"><span className="up">{totals.counts.buy}</span> · <span className="hold">{totals.counts.hold}</span> · <span className="down">{totals.counts.sell}</span></span><span className="s">Buy · Hold · Sell</span></div>
        <div><span className="label">Invested</span><span className="v">{lakhCrore(totals.invested || null)}</span><span className="s">Current {lakhCrore(totals.value || null)}</span></div>
        <div><span className="label">Profit / loss</span><span className={'v ' + tone(totals.invested ? totals.pnl : null)}>{totals.invested ? lakhCrore(totals.pnl) : '—'}</span><span className="s">{totals.invested ? pct((totals.pnl / totals.invested) * 100) : 'Add quantities'}</span></div>
      </section>

      <section>
        <h2>Sectors</h2>
        {data && data.sectors.length === 0 && <div className="empty">Add a ticker or import your Kite holdings to see sector analysis.</div>}
        <div className="cards">
          {data?.sectors.map((s) => <SectorCard key={s.sector} s={s} tickers={data.tickers.filter((r) => (r.ticker.sector || 'Unassigned') === s.sector)} />)}
        </div>
      </section>

      <section>
        <h2>All tickers</h2>
        <div className="ledger">
          <div className="table-box">
            <table>
              <thead>
                <tr>
                  {th('symbol', 'Symbol')}
                  {th('sector', 'Sector')}
                  {th('price', 'Price')}
                  {th('ch1m', '1M')}
                  {th('pe', 'P/E')}
                  <th>52W range</th>
                  {th('pnl', 'P/L')}
                  {th('score', 'Score')}
                  <th>Signal</th>
                  <th><span className="sr">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr><td colSpan={10} className="muted center">No tickers yet.</td></tr>
                )}
                {rows.map((r) => {
                  const q = r.quote, a = r.analysis, t = r.ticker
                  return (
                    <tr key={t.id}>
                      <td>
                        <span className="sym">{t.symbol}</span> <span className="label">{t.exchange}</span>
                        {t.tag === 'holding' && <span className="tag">holding</span>}
                        <div className="muted small">{t.name}</div>
                      </td>
                      <td>{t.sector || <span className="muted">—</span>}</td>
                      <td className="num">{money(q?.price)}</td>
                      <td className={'num ' + tone(q?.ch1m)}>{pct(q?.ch1m)}</td>
                      <td className="num">{num(q?.pe)}</td>
                      <td><RangeBar low={q?.low52} high={q?.high52} price={q?.price} /></td>
                      <td className={'num ' + tone(r.pnl)}>{r.pnl == null ? '—' : money(r.pnl)}</td>
                      <td className="num" title={a.reasons.join(', ')}>
                        {num(a.score)}
                        <div className="muted small">{a.horizon === 'short' ? 'Short-term' : 'Long-term'}{t.horizon_override ? '' : ' (suggested)'}</div>
                      </td>
                      <td className="signal-cell">
                        {a.signal ? <span className={'pill ' + a.signal}>{SIGNAL_LABEL[a.signal]}</span> : <span className="pill na">No data</span>}
                        <div className="muted small">{a.reasons.join(', ')}</div>
                      </td>
                      <td>
                        {confirmId === t.id ? (
                          <span className="row-actions">
                            <button className="ghost danger" onClick={() => remove(t.id)}>Remove</button>
                            <button className="ghost" onClick={() => setConfirmId(null)}>Keep</button>
                          </span>
                        ) : (
                          <span className="row-actions">
                            <button className="ghost" onClick={() => setEditing(t)}>Edit</button>
                            <button className="ghost danger" onClick={() => setConfirmId(t.id)}>Remove</button>
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <TickerForm editing={editing} sectors={sectorNames} onSave={save} onCancel={() => setEditing(null)} />
        </div>
      </section>

      <p className="rules">
        Scores run 0 to 100 from four parts: upside to your target, momentum, valuation against the sector, and room above your stop-loss.
        Short-term tickers weigh momentum most; long-term tickers weigh valuation and upside. 65 and above is Buy, 40 to 64 is Hold, below 40 or at the stop-loss is Sell.
        Sector calls average the scores, weighted by money invested when every ticker has a quantity. These are mechanical screens, not investment advice.
      </p>
    </div>
  )
}

function SectorCard({ s, tickers }: { s: SectorRow; tickers: TickerRow[] }) {
  const total = s.count || 1
  return (
    <article className="card">
      <div className="card-top">
        <div>
          <h3>{s.sector}</h3>
          <span className="muted small">{s.count} ticker{s.count === 1 ? '' : 's'}</span>
        </div>
        {s.call ? <span className={'pill ' + s.call}>{CALL_LABEL[s.call]}</span> : <span className="pill na">No data</span>}
      </div>
      <div className="metrics">
        <div><span className="label">Score</span><span className="num">{num(s.score)}</span></div>
        <div><span className="label">1M</span><span className={'num ' + tone(s.avg_ch1m)}>{pct(s.avg_ch1m)}</span></div>
        <div><span className="label">P/E</span><span className="num">{num(s.avg_pe)}</span></div>
        <div><span className="label">P/L</span><span className={'num ' + tone(s.pnl)}>{lakhCrore(s.pnl)}</span></div>
      </div>
      <div className="mix" aria-label={`Buy ${s.signals.buy}, hold ${s.signals.hold}, sell ${s.signals.sell}`}>
        <span style={{ width: `${(s.signals.buy / total) * 100}%` }} className="bg-up" />
        <span style={{ width: `${(s.signals.hold / total) * 100}%` }} className="bg-hold" />
        <span style={{ width: `${(s.signals.sell / total) * 100}%` }} className="bg-down" />
      </div>
      <div className="chips">
        {tickers.map((r) => (
          <span key={r.ticker.id} className={'chip ' + (r.analysis.signal ?? '')} title={r.analysis.reasons.join(', ')}>
            {r.ticker.symbol} {r.analysis.score == null ? '' : Math.round(r.analysis.score)}
          </span>
        ))}
      </div>
    </article>
  )
}

function RangeBar({ low, high, price }: { low?: number | null; high?: number | null; price?: number | null }) {
  if (low == null || high == null || price == null || high <= low) return <span className="muted">—</span>
  const pos = Math.max(0, Math.min(100, ((price - low) / (high - low)) * 100))
  return (
    <span className="range" title={`52W low ${money(low)}, high ${money(high)}`}>
      <span className="range-track"><span className="range-dot" style={{ left: `${pos}%` }} /></span>
      <span className="muted small">{Math.round(pos)}% of range</span>
    </span>
  )
}

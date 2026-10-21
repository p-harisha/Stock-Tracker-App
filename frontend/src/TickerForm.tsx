import { useEffect, useState } from 'react'
import type { Ticker, TickerInput } from './api'

const EMPTY: TickerInput = {
  exchange: 'NSE',
  symbol: '',
  name: '',
  sector: '',
  tag: 'watching',
  quantity: null,
  avg_price: null,
  target: null,
  stop_loss: null,
  horizon_override: null,
}

interface Props {
  editing: Ticker | null
  sectors: string[]
  onSave: (t: TickerInput, id?: number) => Promise<void>
  onCancel: () => void
}

export default function TickerForm({ editing, sectors, onSave, onCancel }: Props) {
  const [form, setForm] = useState<TickerInput>(EMPTY)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ text: string; err?: boolean } | null>(null)

  useEffect(() => {
    setForm(editing ? { ...editing } : EMPTY)
    setMsg(null)
  }, [editing])

  const set = <K extends keyof TickerInput>(k: K, v: TickerInput[K]) => setForm((f) => ({ ...f, [k]: v }))
  const numField = (k: 'quantity' | 'avg_price' | 'target' | 'stop_loss') => ({
    value: form[k] ?? '',
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => set(k, e.target.value === '' ? null : Number(e.target.value)),
  })

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.symbol.trim()) return setMsg({ text: 'Enter a symbol.', err: true })
    setBusy(true)
    try {
      await onSave({ ...form, symbol: form.symbol.trim().toUpperCase() }, editing?.id)
      setMsg({ text: (editing ? 'Saved ' : 'Added ') + form.symbol.toUpperCase() + '.' })
      if (!editing) setForm(EMPTY)
    } catch (err) {
      setMsg({ text: (err as Error).message, err: true })
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="panel" onSubmit={submit} autoComplete="off">
      <h3>{editing ? `Edit ${editing.exchange}:${editing.symbol}` : 'Add a ticker'}</h3>
      <div className="grid2">
        <label className="field">
          <span>Exchange</span>
          <select value={form.exchange} disabled={!!editing} onChange={(e) => set('exchange', e.target.value as TickerInput['exchange'])}>
            <option>NSE</option>
            <option>BSE</option>
          </select>
        </label>
        <label className="field">
          <span>Symbol</span>
          <input className="mono" required disabled={!!editing} value={form.symbol} onChange={(e) => set('symbol', e.target.value)} placeholder="INFY" />
        </label>
      </div>
      <label className="field">
        <span>Sector (leave empty to fill from market data)</span>
        <input list="sector-list" value={form.sector} onChange={(e) => set('sector', e.target.value)} placeholder="Technology" />
        <datalist id="sector-list">
          {sectors.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
      </label>
      <div className="grid2">
        <label className="field">
          <span>Quantity</span>
          <input type="number" step="any" min="0" {...numField('quantity')} />
        </label>
        <label className="field">
          <span>Avg buy price (₹)</span>
          <input type="number" step="any" min="0" {...numField('avg_price')} />
        </label>
        <label className="field">
          <span>Target (₹)</span>
          <input type="number" step="any" min="0" {...numField('target')} />
        </label>
        <label className="field">
          <span>Stop-loss (₹)</span>
          <input type="number" step="any" min="0" {...numField('stop_loss')} />
        </label>
        <label className="field">
          <span>Tag</span>
          <select value={form.tag} onChange={(e) => set('tag', e.target.value as TickerInput['tag'])}>
            <option value="watching">Watching</option>
            <option value="holding">Holding</option>
          </select>
        </label>
        <label className="field">
          <span>Horizon</span>
          <select
            value={form.horizon_override ?? ''}
            onChange={(e) => set('horizon_override', (e.target.value || null) as TickerInput['horizon_override'])}
          >
            <option value="">Suggested by app</option>
            <option value="short">Short-term</option>
            <option value="long">Long-term</option>
          </select>
        </label>
      </div>
      <div className="actions">
        <button type="submit" className="primary" disabled={busy}>
          {editing ? 'Save changes' : 'Add ticker'}
        </button>
        {editing && (
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
      <p className={'msg' + (msg?.err ? ' err' : '')} role="status">
        {msg?.text}
      </p>
    </form>
  )
}

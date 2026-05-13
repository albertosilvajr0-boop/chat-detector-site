import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { searchAddresses, fmtMoney, type SearchHit } from '../lib/api'

export default function Home() {
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const debounceRef = useRef<number | undefined>(undefined)

  // Debounced search
  useEffect(() => {
    window.clearTimeout(debounceRef.current)
    if (q.trim().length < 3) {
      setHits([]); setError(null); return
    }
    debounceRef.current = window.setTimeout(async () => {
      setLoading(true); setError(null)
      try {
        const r = await searchAddresses(q, 8)
        setHits(r)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Search failed')
        setHits([])
      } finally {
        setLoading(false)
      }
    }, 250)
    return () => window.clearTimeout(debounceRef.current)
  }, [q])

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl sm:text-4xl font-bold text-bcad-700 leading-tight">
        Are you overpaying property taxes on your Bexar County home?
      </h1>
      <p className="mt-3 text-lg text-bcad-900/80">
        Free comparable-property analysis from the 2026 BCAD appraisal roll. Get a
        ready-to-file evidence packet before the&nbsp;
        <span className="font-semibold text-bcad-700">May 15, 2026</span> deadline.
      </p>

      <div className="mt-8 bg-white rounded-lg shadow-sm border border-bcad-100 p-5">
        <label htmlFor="addr" className="block text-sm font-medium text-bcad-700 mb-2">
          Your property address
        </label>
        <input
          id="addr"
          type="text"
          autoComplete="off"
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="e.g. 554 W BROADVIEW DR"
          className="w-full px-4 py-3 border border-bcad-100 rounded-md text-lg focus:outline-none focus:ring-2 focus:ring-bcad-500"
        />
        <p className="mt-2 text-xs text-bcad-900/60">
          Type at least 3 characters. Use uppercase, BCAD format
          (e.g.&nbsp;&quot;1234 OAK ST&quot;). City name is optional.
        </p>

        {error && (
          <div className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
            {error}
          </div>
        )}

        {hits.length > 0 && (
          <ul className="mt-4 border-t border-bcad-100 divide-y divide-bcad-100">
            {hits.map((h) => (
              <li key={h.property_id}>
                <button
                  onClick={() => navigate(`/property/${h.property_id}`)}
                  className="w-full text-left py-3 px-2 hover:bg-bcad-50 rounded transition-colors"
                >
                  <div className="font-medium text-bcad-900">{h.situs_address}</div>
                  <div className="text-xs text-bcad-900/60 mt-0.5 flex justify-between">
                    <span>Owner: {h.owner}</span>
                    <span>BCAD: {fmtMoney(h.appraised_value)}</span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}

        {loading && hits.length === 0 && (
          <p className="mt-4 text-sm text-bcad-900/60">Searching…</p>
        )}
      </div>

      <div className="mt-12 grid sm:grid-cols-3 gap-4 text-sm">
        <Stat headline="99.19%" sub="of Bexar County informal protests in 2024 resulted in a reduction" />
        <Stat headline="2026 = 2027" sub="BCAD moved to biennial appraisal — this year's protest locks in two years" />
        <Stat headline="$571/yr" sub="median annual tax savings on protests where comps support a reduction" />
      </div>
    </div>
  )
}

function Stat({ headline, sub }: { headline: string; sub: string }) {
  return (
    <div className="bg-white border border-bcad-100 rounded-lg p-4">
      <div className="text-2xl font-bold text-bcad-700">{headline}</div>
      <div className="mt-1 text-bcad-900/70">{sub}</div>
    </div>
  )
}

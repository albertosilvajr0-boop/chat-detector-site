import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  countyInfo,
  fmtMoney,
  normalizeCounty,
  searchAddresses,
  type CountyId,
  type SearchHit,
} from '../lib/api'

const COUNTY_COPY: Record<CountyId, { example: string; subhead: string; stats: Array<{ headline: string; sub: string }> }> = {
  bexar: {
    example: '554 W BROADVIEW DR',
    subhead: 'Free comparable-property analysis from the 2026 BCAD appraisal roll.',
    stats: [
      { headline: 'May 15', sub: 'Bexar protest deadline for 2026 appraisals' },
      { headline: 'CB/BLK', sub: 'tight comps from the same BCAD city block when available' },
      { headline: 'PDF packet', sub: 'download evidence when comps support a reduction' },
    ],
  },
  arapahoe: {
    example: '7064 S SPRUCE DR E',
    subhead: 'Free comparable-property analysis from Arapahoe County appraisal data.',
    stats: [
      { headline: 'June 8', sub: 'Arapahoe real property appeal deadline for 2026' },
      { headline: 'Neighborhood', sub: 'tight comps by neighborhood code and property type' },
      { headline: 'PDF packet', sub: 'download evidence when comps support a reduction' },
    ],
  },
}

export default function Home() {
  const [searchParams] = useSearchParams()
  const county = normalizeCounty(searchParams.get('county') || undefined)
  const info = countyInfo(county)
  const copy = COUNTY_COPY[county]
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const debounceRef = useRef<number | undefined>(undefined)

  useEffect(() => {
    setQ('')
    setHits([])
    setError(null)
  }, [county])

  useEffect(() => {
    window.clearTimeout(debounceRef.current)
    if (q.trim().length < 3) {
      setHits([])
      setError(null)
      return
    }
    debounceRef.current = window.setTimeout(async () => {
      setLoading(true)
      setError(null)
      try {
        const r = await searchAddresses(county, q, 8)
        setHits(r)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Search failed')
        setHits([])
      } finally {
        setLoading(false)
      }
    }, 250)
    return () => window.clearTimeout(debounceRef.current)
  }, [county, q])

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-bcad-900/50">
          More counties coming
        </p>
      </div>

      <h1 className="text-3xl sm:text-4xl font-bold text-bcad-700 leading-tight">
        Are you overpaying property taxes in {info.label}?
      </h1>
      <p className="mt-3 text-lg text-bcad-900/80">
        {copy.subhead} Check your address against nearby comparable homes and get a
        ready-to-use evidence packet before the{' '}
        <span className="font-semibold text-bcad-700">{info.deadline}</span> deadline.
      </p>

      <div className="mt-8 bg-white rounded-lg shadow-sm border border-bcad-100 p-5">
        <label htmlFor="addr" className="block text-sm font-medium text-bcad-700 mb-2">
          Your {info.label} property address
        </label>
        <input
          id="addr"
          type="text"
          autoComplete="off"
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={`e.g. ${copy.example}`}
          className="w-full px-4 py-3 border border-bcad-100 rounded-md text-lg focus:outline-none focus:ring-2 focus:ring-bcad-500"
        />
        <p className="mt-2 text-xs text-bcad-900/60">
          Type at least 3 characters. Search by address or owner name.
        </p>

        {error && (
          <div className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
            {error}
          </div>
        )}

        {hits.length > 0 && (
          <ul className="mt-4 border-t border-bcad-100 divide-y divide-bcad-100">
            {hits.map((h) => (
              <li key={`${h.county}-${h.property_id}`}>
                <button
                  onClick={() => navigate(`/property/${h.county}/${encodeURIComponent(h.property_id)}`)}
                  className="w-full text-left py-3 px-2 hover:bg-bcad-50 rounded transition-colors"
                >
                  <div className="font-medium text-bcad-900">{h.situs_address}</div>
                  <div className="text-xs text-bcad-900/60 mt-0.5 flex flex-col gap-1 sm:flex-row sm:justify-between">
                    <span>Owner: {h.owner}</span>
                    <span>{h.assessor_label}: {fmtMoney(h.appraised_value)}</span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}

        {loading && hits.length === 0 && (
          <p className="mt-4 text-sm text-bcad-900/60">Searching...</p>
        )}
      </div>

      <div className="mt-12 grid sm:grid-cols-3 gap-4 text-sm">
        {copy.stats.map((stat) => (
          <Stat key={stat.headline} headline={stat.headline} sub={stat.sub} />
        ))}
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

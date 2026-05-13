/**
 * Client for the Cloud Run backend. Base URL comes from VITE_API_BASE_URL.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

export interface SearchHit {
  property_id: number
  situs_address: string
  owner: string
  appraised_value: number
  zip_code: number
}

export interface Comp {
  property_id: number
  situs_address: string
  appraised_value: number
  market_value: number | null
  assessed_value: number
  legal_description: string
  has_homestead: boolean
}

export interface Subject {
  PropertyId: number
  GeoId: string
  SitusAddress: string
  OwnerFullName: string
  ZipCode: number
  CB: string | null
  BLK: string | null
  MarketValue: number | null
  AppraisedValue: number
  AssessedValue: number
  LegalDescription: string
  HasHomestead: boolean
}

export type ReasonCode =
  | 'overassessed_vs_comps'
  | 'not_overassessed'
  | 'reduction_too_small'
  | 'large_reduction_needs_human_review'
  | 'parcel_not_found'
  | string  // tolerates "insufficient_comps (N found, need 5)"

export interface CompAnalysis {
  subject: Subject
  comps: Comp[]
  comp_count_total: number
  geography_tier_used: 'CB+BLK' | 'CB' | 'none' | ''
  median_appraised: number | null
  median_market: number | null
  target_value: number | null
  estimated_reduction: number | null
  estimated_pct_reduction: number | null
  estimated_annual_tax_savings: number | null
  is_protestable: boolean
  reason: ReasonCode
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return res.json() as Promise<T>
}

export async function searchAddresses(query: string, limit = 10): Promise<SearchHit[]> {
  const url = new URL(`${API_BASE}/search`)
  url.searchParams.set('q', query)
  url.searchParams.set('limit', String(limit))
  const res = await fetch(url.toString())
  const data = await jsonOrThrow<{ results: SearchHit[] }>(res)
  return data.results
}

export async function analyzeParcel(propertyId: number): Promise<CompAnalysis> {
  const res = await fetch(`${API_BASE}/analyze/${propertyId}`)
  return jsonOrThrow<CompAnalysis>(res)
}

export function packetUrl(propertyId: number): string {
  return `${API_BASE}/packet/${propertyId}`
}

export function fmtMoney(v: number | null | undefined, fallback = '—'): string {
  if (v == null) return fallback
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', maximumFractionDigits: 0,
  }).format(v)
}

export function fmtPct(v: number | null | undefined, fallback = '—'): string {
  if (v == null) return fallback
  return `${v.toFixed(1)}%`
}

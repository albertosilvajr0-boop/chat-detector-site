/**
 * Client for the Cloud Run backend. Base URL comes from VITE_API_BASE_URL.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

export type CountyId = 'bexar' | 'arapahoe'

export interface CountyInfo {
  id: CountyId
  label: string
  short_label: string
  assessor_label: string
  assessor_short: string
  property_id_label: string
  appraisal_label: string
  appeal_label: string
  deadline: string
  evidence_basis: string
  data_source: string
  filing_url: string
}

export const COUNTY_OPTIONS: CountyInfo[] = [
  {
    id: 'bexar',
    label: 'Bexar County',
    short_label: 'Bexar',
    assessor_label: 'Bexar Central Appraisal District',
    assessor_short: 'BCAD',
    property_id_label: 'BCAD Property ID',
    appraisal_label: 'BCAD Appraised',
    appeal_label: 'protest',
    deadline: 'May 15, 2026',
    evidence_basis: 'Texas Tax Code Section 41.43(b)(3) unequal appraisal',
    data_source: '2026 BCAD certified appraisal roll',
    filing_url: 'https://bcad.org',
  },
  {
    id: 'arapahoe',
    label: 'Arapahoe County',
    short_label: 'Arapahoe',
    assessor_label: 'Arapahoe County Assessor',
    assessor_short: 'Arapahoe Assessor',
    property_id_label: 'Arapahoe Parcel ID',
    appraisal_label: 'Assessor Value',
    appeal_label: 'appeal',
    deadline: 'June 8, 2026',
    evidence_basis: 'Colorado real property valuation appeal evidence',
    data_source: 'Arapahoe County appraisal roll',
    filing_url: 'https://www.arapahoeco.gov/assessor',
  },
]

export function normalizeCounty(value: string | undefined): CountyId {
  return value === 'arapahoe' ? 'arapahoe' : 'bexar'
}

export function countyInfo(id: CountyId): CountyInfo {
  return COUNTY_OPTIONS.find((county) => county.id === id) ?? COUNTY_OPTIONS[0]
}

export interface SearchHit {
  property_id: string
  county: CountyId
  county_label: string
  situs_address: string
  owner: string
  appraised_value: number
  zip_code: number
  assessor_label: string
}

export interface Comp {
  property_id: string
  county: CountyId
  situs_address: string
  appraised_value: number
  market_value: number | null
  assessed_value: number | null
  legal_description: string
  neighborhood: string
  property_use: string
  has_homestead: boolean
}

export interface Subject {
  County: CountyId
  PropertyId: string
  GeoId: string
  ZipCode: number
  DistanceFromAnchor: number | null
  OwnerFullName: string
  SitusAddress: string
  NormAddr: string
  LegalDescription: string
  NeighborhoodCode: string | null
  Neighborhood: string | null
  PropertyUse: string | null
  PropertyUseGroup: string | null
  MarketValue: number | null
  AppraisedValue: number
  AssessedValue: number | null
  LandValue: number | null
  ImprovementValue: number | null
  Year: number
  GroupCodes: string | null
  CB: string | null
  BLK: string | null
  HasHomestead: boolean
  CoordinateX: number | null
  CoordinateY: number | null
  SaleDate: string | null
  SalePrice: number | null
}

export type ReasonCode =
  | 'overassessed_vs_comps'
  | 'not_overassessed'
  | 'reduction_too_small'
  | 'large_reduction_needs_human_review'
  | 'parcel_not_found'
  | string

export interface CompAnalysis {
  county: CountyInfo
  subject: Subject
  comps: Comp[]
  comp_count_total: number
  geography_tier_used: string
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

export async function searchAddresses(
  county: CountyId,
  query: string,
  limit = 10,
): Promise<SearchHit[]> {
  const url = new URL(`${API_BASE}/search`)
  url.searchParams.set('county', county)
  url.searchParams.set('q', query)
  url.searchParams.set('limit', String(limit))
  const res = await fetch(url.toString())
  const data = await jsonOrThrow<{ results: SearchHit[] }>(res)
  return data.results
}

export async function analyzeParcel(
  county: CountyId,
  propertyId: string,
): Promise<CompAnalysis> {
  const res = await fetch(`${API_BASE}/analyze/${county}/${encodeURIComponent(propertyId)}`)
  return jsonOrThrow<CompAnalysis>(res)
}

export function packetUrl(county: CountyId, propertyId: string): string {
  return `${API_BASE}/packet/${county}/${encodeURIComponent(propertyId)}`
}

export function protestCandidatesCsvUrl(county: CountyId | 'all'): string {
  const url = new URL(`${API_BASE}/admin/protest-candidates.csv`)
  url.searchParams.set('county', county)
  return url.toString()
}

export function fmtMoney(v: number | null | undefined, fallback = '-'): string {
  if (v == null) return fallback
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(v)
}

export function fmtPct(v: number | null | undefined, fallback = '-'): string {
  if (v == null) return fallback
  return `${v.toFixed(1)}%`
}

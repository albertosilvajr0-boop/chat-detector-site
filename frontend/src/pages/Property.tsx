import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  analyzeParcel,
  fmtMoney,
  fmtPct,
  normalizeCounty,
  packetUrl,
  type CompAnalysis,
} from '../lib/api'
import { captureLead } from '../lib/firebase'

export default function Property() {
  const { county: countyParam, propertyId } = useParams<{ county?: string; propertyId: string }>()
  const county = normalizeCounty(countyParam)
  const navigate = useNavigate()
  const [analysis, setAnalysis] = useState<CompAnalysis | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!propertyId) return
    setAnalysis(null)
    setError(null)
    analyzeParcel(county, propertyId)
      .then(setAnalysis)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load'))
  }, [county, propertyId])

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <p className="text-red-700">Error: {error}</p>
        <Link to={`/?county=${county}`} className="text-bcad-700 underline mt-4 inline-block">
          Back to search
        </Link>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-bcad-900/60">
        Analyzing...
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <Link to={`/?county=${analysis.county.id}`} className="text-sm text-bcad-700 hover:underline">
        Search another {analysis.county.short_label} address
      </Link>

      <h1 className="mt-4 text-2xl font-bold text-bcad-700">
        {analysis.subject.SitusAddress}
      </h1>
      <p className="text-sm text-bcad-900/70">
        Owner: {analysis.subject.OwnerFullName} &middot; {analysis.county.property_id_label}{' '}
        {analysis.subject.PropertyId}
      </p>

      {analysis.is_protestable
        ? <Protestable analysis={analysis} onLeadCaptured={() => navigate('/thanks')} />
        : <NotProtestable analysis={analysis} />}
    </div>
  )
}

function Protestable({
  analysis,
  onLeadCaptured,
}: {
  analysis: CompAnalysis
  onLeadCaptured: () => void
}) {
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitErr, setSubmitErr] = useState<string | null>(null)
  const savingsValue = analysis.estimated_annual_tax_savings == null
    ? 'Varies by tax district'
    : fmtMoney(analysis.estimated_annual_tax_savings)

  async function handleDownload(e: FormEvent) {
    e.preventDefault()
    if (!email || !email.includes('@')) {
      setSubmitErr('Please enter a valid email')
      return
    }
    setSubmitting(true)
    setSubmitErr(null)
    try {
      await captureLead({
        email,
        county: analysis.county.id,
        countyLabel: analysis.county.label,
        propertyId: analysis.subject.PropertyId,
        situsAddress: analysis.subject.SitusAddress,
        owner: analysis.subject.OwnerFullName,
        appraisedValue: analysis.subject.AppraisedValue,
        targetValue: analysis.target_value ?? undefined,
        estimatedReduction: analysis.estimated_reduction ?? undefined,
        estimatedSavings: analysis.estimated_annual_tax_savings ?? undefined,
        isProtestable: true,
        requestType: 'packet',
        reason: analysis.reason,
      })
      window.open(packetUrl(analysis.county.id, analysis.subject.PropertyId), '_blank')
      setTimeout(onLeadCaptured, 600)
    } catch (e: unknown) {
      setSubmitErr(e instanceof Error ? e.message : 'Could not save your email')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <div className="mt-6 grid sm:grid-cols-4 gap-3">
        <Card label={analysis.county.appraisal_label} value={fmtMoney(analysis.subject.AppraisedValue)} />
        <Card label="Recommended Value" value={fmtMoney(analysis.target_value)} />
        <Card
          label="Estimated Reduction"
          value={`${fmtMoney(analysis.estimated_reduction)} (${fmtPct(analysis.estimated_pct_reduction)})`}
          accent
        />
        <Card
          label="Tax Impact"
          value={savingsValue}
          accent={analysis.estimated_annual_tax_savings != null}
        />
      </div>

      <p className="mt-6 text-bcad-900/80">
        Your {analysis.county.assessor_short} value of{' '}
        <strong>{fmtMoney(analysis.subject.AppraisedValue)}</strong> exceeds the median of{' '}
        {analysis.comp_count_total} comparable properties in the{' '}
        <strong>{analysis.geography_tier_used}</strong> comp set (median:{' '}
        <strong>{fmtMoney(analysis.median_appraised)}</strong>). This may support a{' '}
        {analysis.county.appeal_label} using {analysis.county.evidence_basis}.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-bcad-700">Comparable properties</h2>
      <CompTable analysis={analysis} />

      <div className="mt-8 bg-white border border-bcad-100 rounded-lg p-5">
        <h2 className="text-lg font-semibold text-bcad-700">
          Get your evidence packet
        </h2>
        <p className="mt-1 text-sm text-bcad-900/70">
          A PDF packet with the comp grid, methodology, and filing notes for your{' '}
          {analysis.county.label} {analysis.county.appeal_label}. Free.
        </p>
        <form onSubmit={handleDownload} className="mt-4 flex flex-col sm:flex-row gap-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="flex-1 px-4 py-2 border border-bcad-100 rounded-md focus:outline-none focus:ring-2 focus:ring-bcad-500"
          />
          <button
            type="submit"
            disabled={submitting}
            className="bg-bcad-700 text-white px-5 py-2 rounded-md hover:bg-bcad-900 disabled:opacity-50"
          >
            {submitting ? 'Preparing...' : 'Download evidence packet'}
          </button>
        </form>
        {submitErr && <p className="mt-2 text-sm text-red-700">{submitErr}</p>}
        <p className="mt-3 text-xs text-bcad-900/50">
          We store your email with this address so you can receive deadline reminders and follow-up tips.
          No spam, no sharing.
        </p>
      </div>
    </>
  )
}

function NotProtestable({ analysis }: { analysis: CompAnalysis }) {
  const isInsufficient = analysis.reason.startsWith('insufficient_comps')
  const isNotOver = analysis.reason === 'not_overassessed'
  const isFlagged = analysis.reason === 'large_reduction_needs_human_review'

  return (
    <div className="mt-6 bg-white border border-bcad-100 rounded-lg p-5">
      {isNotOver && (
        <>
          <h2 className="text-lg font-semibold text-bcad-700">
            Your value looks in range
          </h2>
          <p className="mt-2 text-bcad-900/80">
            Your {analysis.county.assessor_short} value of{' '}
            <strong>{fmtMoney(analysis.subject.AppraisedValue)}</strong> is at or below the
            median of {analysis.comp_count_total} tight comparable properties (
            <strong>{fmtMoney(analysis.median_appraised)}</strong>). This comparable-value
            screen does not support a reduction, but condition issues, recent purchase price,
            or recent nearby sales may still matter.
          </p>
        </>
      )}
      {isInsufficient && (
        <>
          <h2 className="text-lg font-semibold text-bcad-700">
            Not enough tight comparable properties
          </h2>
          <p className="mt-2 text-bcad-900/80">
            We could not find at least 5 comparable properties using this county's tight
            comp rules. Filing may still be worthwhile if you have recent sales, condition
            photos, repair estimates, or other property-specific evidence.
          </p>
        </>
      )}
      {isFlagged && (
        <>
          <h2 className="text-lg font-semibold text-bcad-700">
            This property needs a second look
          </h2>
          <p className="mt-2 text-bcad-900/80">
            The math suggests a large reduction, but the public data is too coarse to
            claim it confidently without human review. Leave your email below and we will
            follow up.
          </p>
        </>
      )}

      <div className="mt-5 rounded bg-bcad-50 border border-bcad-100 p-4 text-sm">
        <p className="font-semibold text-bcad-700">
          Deadline: {analysis.county.deadline}
        </p>
        <p className="mt-1 text-bcad-900/80">
          You remain responsible for filing your own {analysis.county.label}{' '}
          {analysis.county.appeal_label}. This tool is a screening aid built from public
          appraisal data.
        </p>
      </div>

      <InfoRequestForm analysis={analysis} />
    </div>
  )
}

function InfoRequestForm({ analysis }: { analysis: CompAnalysis }) {
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitErr, setSubmitErr] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!email || !email.includes('@')) {
      setSubmitErr('Please enter a valid email')
      return
    }

    setSubmitting(true)
    setSubmitErr(null)
    try {
      await captureLead({
        email,
        county: analysis.county.id,
        countyLabel: analysis.county.label,
        propertyId: analysis.subject.PropertyId,
        situsAddress: analysis.subject.SitusAddress,
        owner: analysis.subject.OwnerFullName,
        appraisedValue: analysis.subject.AppraisedValue,
        targetValue: analysis.target_value ?? undefined,
        estimatedReduction: analysis.estimated_reduction ?? undefined,
        estimatedSavings: analysis.estimated_annual_tax_savings ?? undefined,
        isProtestable: analysis.is_protestable,
        requestType: 'info',
        reason: analysis.reason,
      })
      setSubmitted(true)
    } catch (e: unknown) {
      setSubmitErr(e instanceof Error ? e.message : 'Could not save your email')
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <p className="mt-5 rounded bg-emerald-50 border border-emerald-100 p-4 text-sm font-semibold text-money">
        Thanks. Your address and email were saved for follow-up.
      </p>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="mt-5 rounded border border-bcad-100 bg-white p-4">
      <h2 className="text-sm font-semibold text-bcad-700">Send me this address summary</h2>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="flex-1 px-4 py-2 border border-bcad-100 rounded-md focus:outline-none focus:ring-2 focus:ring-bcad-500"
        />
        <button
          type="submit"
          disabled={submitting}
          className="bg-bcad-700 text-white px-5 py-2 rounded-md hover:bg-bcad-900 disabled:opacity-50"
        >
          {submitting ? 'Saving...' : 'Send summary'}
        </button>
      </div>
      {submitErr && <p className="mt-2 text-sm text-red-700">{submitErr}</p>}
      <p className="mt-3 text-xs text-bcad-900/50">
        We store the email with this county, property address, and value summary.
      </p>
    </form>
  )
}

function Card({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="bg-white border border-bcad-100 rounded-lg p-3">
      <div className="text-xs text-bcad-900/60">{label}</div>
      <div className={`mt-1 font-bold text-lg ${accent ? 'text-money' : 'text-bcad-900'}`}>
        {value}
      </div>
    </div>
  )
}

function CompTable({ analysis }: { analysis: CompAnalysis }) {
  return (
    <div className="mt-3 overflow-x-auto bg-white border border-bcad-100 rounded-lg">
      <table className="w-full text-sm">
        <thead className="bg-bcad-700 text-white">
          <tr>
            <th className="text-left px-3 py-2">#</th>
            <th className="text-left px-3 py-2">Address</th>
            <th className="text-right px-3 py-2">{analysis.county.appraisal_label}</th>
            <th className="text-right px-3 py-2">vs. Your Value</th>
          </tr>
        </thead>
        <tbody>
          <tr className="bg-amber-50 font-semibold">
            <td className="px-3 py-2">*</td>
            <td className="px-3 py-2">YOU - {analysis.subject.SitusAddress}</td>
            <td className="px-3 py-2 text-right">{fmtMoney(analysis.subject.AppraisedValue)}</td>
            <td className="px-3 py-2 text-right">-</td>
          </tr>
          {analysis.comps.map((c, i) => {
            const diff = c.appraised_value - analysis.subject.AppraisedValue
            return (
              <tr key={`${c.county}-${c.property_id}`} className="cmp-row">
                <td className="px-3 py-2 text-bcad-900/50">{i + 1}</td>
                <td className="px-3 py-2">{c.situs_address}</td>
                <td className="px-3 py-2 text-right">{fmtMoney(c.appraised_value)}</td>
                <td className={`px-3 py-2 text-right ${diff < 0 ? 'text-money' : 'text-bcad-900/60'}`}>
                  {diff < 0 ? '-' : '+'}{fmtMoney(Math.abs(diff))}
                </td>
              </tr>
            )
          })}
          <tr className="bg-emerald-50 font-semibold text-money border-t-2 border-bcad-700">
            <td className="px-3 py-2"></td>
            <td className="px-3 py-2">Median of comparables</td>
            <td className="px-3 py-2 text-right">{fmtMoney(analysis.median_appraised)}</td>
            <td className="px-3 py-2 text-right">
              {fmtMoney((analysis.median_appraised ?? 0) - analysis.subject.AppraisedValue)}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

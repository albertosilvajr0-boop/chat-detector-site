import { useEffect, useState, type FormEvent } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  analyzeParcel, packetUrl, fmtMoney, fmtPct, type CompAnalysis,
} from '../lib/api'
import { captureLead } from '../lib/firebase'

export default function Property() {
  const { propertyId } = useParams<{ propertyId: string }>()
  const navigate = useNavigate()
  const [analysis, setAnalysis] = useState<CompAnalysis | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!propertyId) return
    analyzeParcel(parseInt(propertyId, 10))
      .then(setAnalysis)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load'))
  }, [propertyId])

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <p className="text-red-700">Error: {error}</p>
        <Link to="/" className="text-bcad-700 underline mt-4 inline-block">
          ← Try another address
        </Link>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-bcad-900/60">
        Analyzing…
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <Link to="/" className="text-sm text-bcad-700 hover:underline">
        ← Search another address
      </Link>

      <h1 className="mt-4 text-2xl font-bold text-bcad-700">
        {analysis.subject.SitusAddress}
      </h1>
      <p className="text-sm text-bcad-900/70">
        Owner: {analysis.subject.OwnerFullName} &middot; BCAD Property ID&nbsp;
        {analysis.subject.PropertyId}
      </p>

      {analysis.is_protestable
        ? <Protestable analysis={analysis} onLeadCaptured={() => navigate('/thanks')} />
        : <NotProtestable analysis={analysis} />}
    </div>
  )
}

function Protestable({
  analysis, onLeadCaptured,
}: {
  analysis: CompAnalysis
  onLeadCaptured: () => void
}) {
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitErr, setSubmitErr] = useState<string | null>(null)

  async function handleDownload(e: FormEvent) {
    e.preventDefault()
    if (!email || !email.includes('@')) {
      setSubmitErr('Please enter a valid email')
      return
    }
    setSubmitting(true); setSubmitErr(null)
    try {
      await captureLead({
        email,
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
      // Trigger PDF download in a new tab; navigate to thanks page after.
      window.open(packetUrl(analysis.subject.PropertyId), '_blank')
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
        <Card label="BCAD Appraised" value={fmtMoney(analysis.subject.AppraisedValue)} />
        <Card label="Recommended Value" value={fmtMoney(analysis.target_value)} />
        <Card
          label="Estimated Reduction"
          value={`${fmtMoney(analysis.estimated_reduction)} (${fmtPct(analysis.estimated_pct_reduction)})`}
          accent
        />
        <Card
          label="Annual Tax Savings"
          value={fmtMoney(analysis.estimated_annual_tax_savings)}
          accent
        />
      </div>

      <p className="mt-6 text-bcad-900/80">
        Your BCAD appraisal of <strong>{fmtMoney(analysis.subject.AppraisedValue)}</strong>
        &nbsp;exceeds the median of {analysis.comp_count_total} comparable properties
        in the same {analysis.geography_tier_used === 'CB+BLK' ? 'city block (BLK)' : 'city block'}
        &nbsp;(median: <strong>{fmtMoney(analysis.median_appraised)}</strong>). This is
        grounds for a protest under <em>Tex. Tax Code §41.43(b)(3)</em>.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-bcad-700">Comparable properties</h2>
      <CompTable analysis={analysis} />

      <div className="mt-8 bg-white border border-bcad-100 rounded-lg p-5">
        <h2 className="text-lg font-semibold text-bcad-700">
          Get your evidence packet
        </h2>
        <p className="mt-1 text-sm text-bcad-900/70">
          A 4-page PDF you attach to your BCAD E-File protest. Includes the comp grid,
          methodology, and filing instructions. Free.
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
            {submitting ? 'Preparing…' : 'Download evidence packet'}
          </button>
        </form>
        {submitErr && (
          <p className="mt-2 text-sm text-red-700">{submitErr}</p>
        )}
        <p className="mt-3 text-xs text-bcad-900/50">
          We&apos;ll email you reminders about the May 15 deadline and follow-up tips.
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
            Your appraisal looks fair
          </h2>
          <p className="mt-2 text-bcad-900/80">
            Your BCAD appraisal of <strong>{fmtMoney(analysis.subject.AppraisedValue)}</strong>
            &nbsp;is at or below the median of {analysis.comp_count_total} comparable
            properties (<strong>{fmtMoney(analysis.median_appraised)}</strong>). Our
            unequal-appraisal analysis doesn&apos;t support a reduction. You may still
            have other grounds — recent storm damage, deferred maintenance, or a
            recent purchase price below BCAD&apos;s value all justify protesting.
          </p>
        </>
      )}
      {isInsufficient && (
        <>
          <h2 className="text-lg font-semibold text-bcad-700">
            Not enough nearby comparable properties
          </h2>
          <p className="mt-2 text-bcad-900/80">
            We couldn&apos;t find at least 5 comparable properties in the same city
            block. This usually happens with acreage parcels, condos, or properties
            in newer subdivisions. Filing a protest is still worthwhile — you just
            need different evidence (recent sales, condition photos, contractor
            estimates).
          </p>
        </>
      )}
      {isFlagged && (
        <>
          <h2 className="text-lg font-semibold text-bcad-700">
            This property needs a second look
          </h2>
          <p className="mt-2 text-bcad-900/80">
            Our analysis suggests a large reduction, but the data is too coarse to
            credibly assert that without seeing the property in person. Leave your
            email below and we&apos;ll follow up.
          </p>
        </>
      )}

      <div className="mt-5 rounded bg-bcad-50 border border-bcad-100 p-4 text-sm">
        <p className="font-semibold text-bcad-700">
          File anyway by Friday, May 15
        </p>
        <p className="mt-1 text-bcad-900/80">
          2026 is the first <strong>biennial</strong> year — your locked value sets
          the baseline for 2027 too. Protesting has zero downside; your value can&apos;t
          increase as a result. File Form&nbsp;50-132 on bcad.org with your Owner ID
          and PIN.
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
        We store the email with this property address so you can get follow-up help.
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
            <th className="text-right px-3 py-2">BCAD Appraised</th>
            <th className="text-right px-3 py-2">vs. Your Value</th>
          </tr>
        </thead>
        <tbody>
          <tr className="bg-amber-50 font-semibold">
            <td className="px-3 py-2">★</td>
            <td className="px-3 py-2">YOU — {analysis.subject.SitusAddress}</td>
            <td className="px-3 py-2 text-right">{fmtMoney(analysis.subject.AppraisedValue)}</td>
            <td className="px-3 py-2 text-right">—</td>
          </tr>
          {analysis.comps.map((c, i) => {
            const diff = c.appraised_value - analysis.subject.AppraisedValue
            return (
              <tr key={c.property_id} className="cmp-row">
                <td className="px-3 py-2 text-bcad-900/50">{i + 1}</td>
                <td className="px-3 py-2">{c.situs_address}</td>
                <td className="px-3 py-2 text-right">{fmtMoney(c.appraised_value)}</td>
                <td className={`px-3 py-2 text-right ${diff < 0 ? 'text-money' : 'text-bcad-900/60'}`}>
                  {diff < 0 ? '−' : '+'}{fmtMoney(Math.abs(diff))}
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

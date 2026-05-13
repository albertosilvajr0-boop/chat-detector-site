import { Link } from 'react-router-dom'

export default function Thanks() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-bcad-700">
        Your packet is downloading.
      </h1>
      <p className="mt-3 text-lg text-bcad-900/80">
        Now finish filing your protest with BCAD — it takes about 10 minutes.
      </p>

      <ol className="mt-8 space-y-6">
        <Step n={1} title="File Form 50-132 on bcad.org">
          Go to <a className="text-bcad-700 underline" href="https://bcad.org" target="_blank" rel="noreferrer">bcad.org</a> and click
          &quot;E-File Your Protest.&quot; You&apos;ll need your Owner ID and PIN from
          your Notice of Appraised Value (NOAV). If you didn&apos;t receive one,
          look up your property on the BCAD site to request the PIN.
          <strong className="block mt-2">Check BOTH grounds to preserve your rights:</strong>
          <span className="block mt-1 ml-4">☑ Incorrect appraised (market) value</span>
          <span className="block ml-4">☑ Value is unequal compared with other properties</span>
        </Step>

        <Step n={2} title="Upload the PDF you just downloaded">
          On the E-File portal, attach your evidence packet. Also check the box
          requesting BCAD&apos;s evidence under Tex. Tax Code §41.461 — they must
          give you their comparables 14 days before the hearing.
        </Step>

        <Step n={3} title="Attend the informal hearing">
          BCAD schedules a phone, video, or in-person hearing 30-90 days after
          you file. The appraiser will likely offer a value reduction —
          <strong> 99.19% of Bexar County informal protests result in a reduction</strong>.
          Bring photos of any condition issues (cracked foundation, roof damage,
          etc.) along with the packet.
        </Step>

        <Step n={4} title="Pay your taxes by January 31, 2027">
          Filing a protest does not delay your tax payment deadline. Pay based
          on the current value; any overpayment from a successful protest gets
          refunded.
        </Step>
      </ol>

      <div className="mt-10 p-4 bg-bcad-100 rounded-lg text-sm">
        <p className="font-semibold text-bcad-700">Deadline: Friday, May 15, 2026 at 11:59 PM Central</p>
        <p className="mt-1 text-bcad-900/80">
          Late protests require &quot;good cause&quot; under Tex. Tax Code §41.44(b) and are
          accepted at the ARB&apos;s discretion only. Don&apos;t wait.
        </p>
      </div>

      <p className="mt-8 text-sm">
        <Link to="/" className="text-bcad-700 underline">
          ← Analyze another property
        </Link>
      </p>
    </div>
  )
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <li className="flex gap-4">
      <div className="flex-none w-9 h-9 rounded-full bg-bcad-700 text-white font-bold flex items-center justify-center">
        {n}
      </div>
      <div className="flex-1">
        <h3 className="font-semibold text-bcad-700">{title}</h3>
        <div className="mt-1 text-bcad-900/80">{children}</div>
      </div>
    </li>
  )
}

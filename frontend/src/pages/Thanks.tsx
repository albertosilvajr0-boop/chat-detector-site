import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export default function Thanks() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-bcad-700">
        Your packet is downloading.
      </h1>
      <p className="mt-3 text-lg text-bcad-900/80">
        Now file your county protest or appeal and attach the PDF as comparable-value evidence.
      </p>

      <ol className="mt-8 space-y-6">
        <Step n={1} title="File with the correct county">
          Use the county selected in the tool. Bexar homeowners file through BCAD.
          Arapahoe homeowners file through the Arapahoe County Assessor appeal process.
        </Step>

        <Step n={2} title="Upload the PDF you just downloaded">
          Attach your evidence packet and keep a copy for your records. The packet includes
          the subject property, comp set, median value, and requested value adjustment.
        </Step>

        <Step n={3} title="Add property-specific proof">
          Photos, repair estimates, recent purchase documents, and nearby sales can make the
          packet stronger, especially when the public appraisal roll does not capture condition.
        </Step>

        <Step n={4} title="Watch your county deadline">
          Filing windows vary by county. Check the official county assessor site before the
          deadline and save any confirmation number after you file.
        </Step>
      </ol>

      <p className="mt-8 text-sm">
        <Link to="/" className="text-bcad-700 underline">
          Analyze another property
        </Link>
      </p>
    </div>
  )
}

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
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

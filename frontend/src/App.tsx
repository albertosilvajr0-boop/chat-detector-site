import { Routes, Route, Link } from 'react-router-dom'
import AdminWidget from './components/AdminWidget'
import Home from './pages/Home'
import Property from './pages/Property'
import Thanks from './pages/Thanks'

export default function App() {
  return (
    <div className="min-h-full flex flex-col">
      <header className="bg-bcad-700 text-white">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="font-bold text-lg">
            Bexar Protest Helper
          </Link>
          <a
            href="https://bcad.org"
            target="_blank"
            rel="noreferrer noopener"
            className="text-sm text-bcad-100 hover:text-white"
          >
            BCAD&nbsp;↗
          </a>
        </div>
      </header>

      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/property/:propertyId" element={<Property />} />
          <Route path="/thanks" element={<Thanks />} />
        </Routes>
      </main>

      <footer className="bg-bcad-900 text-bcad-100 text-xs py-6 mt-12">
        <div className="max-w-5xl mx-auto px-4">
          <p className="mb-1">
            Not affiliated with the Bexar Central Appraisal District. Data sourced from the 2026 BCAD certified appraisal roll.
          </p>
          <p>
            This tool generates evidence; the homeowner remains responsible for filing Form 50-132 with their own Owner ID and PIN before the
            May&nbsp;15,&nbsp;2026 deadline.
          </p>
        </div>
      </footer>

      <AdminWidget />
    </div>
  )
}

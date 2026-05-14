import { Link, Route, Routes } from 'react-router-dom'
import AdminWidget from './components/AdminWidget'
import Home from './pages/Home'
import Property from './pages/Property'
import Thanks from './pages/Thanks'

export default function App() {
  return (
    <div className="min-h-full flex flex-col">
      <header className="bg-bcad-700 text-white">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <Link to="/" className="font-bold text-lg">
            Bexar + Arapahoe Protest Helper
          </Link>
          <span className="text-xs font-semibold uppercase tracking-wide text-bcad-100">
            More counties coming
          </span>
        </div>
      </header>

      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/property/:county/:propertyId" element={<Property />} />
          <Route path="/property/:propertyId" element={<Property />} />
          <Route path="/thanks" element={<Thanks />} />
        </Routes>
      </main>

      <footer className="bg-bcad-900 text-bcad-100 text-xs py-6 mt-12">
        <div className="max-w-5xl mx-auto px-4">
          <p className="mb-1">
            Built with public county appraisal data. Not affiliated with or endorsed by BCAD or Arapahoe County.
          </p>
          <p>
            This tool generates evidence; homeowners remain responsible for filing their own protest or appeal before the applicable county deadline.
          </p>
        </div>
      </footer>

      <AdminWidget />
    </div>
  )
}

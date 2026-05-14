import { Link, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import AdminWidget from './components/AdminWidget'
import Home from './pages/Home'
import Property from './pages/Property'
import Thanks from './pages/Thanks'
import { COUNTY_OPTIONS, normalizeCounty, type CountyId } from './lib/api'

export default function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const activeCounty = currentCounty(location.pathname, location.search)

  function selectCounty(county: CountyId) {
    navigate(county === 'bexar' ? '/' : `/?county=${county}`)
  }

  return (
    <div className="min-h-full flex flex-col">
      <header className="bg-bcad-700 text-white">
        <div className="max-w-5xl mx-auto px-4 py-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <Link to="/" className="font-bold text-lg leading-tight">
            Bexar + Arapahoe Protest Helper
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-md border border-white/20 bg-white/10 p-1">
              {COUNTY_OPTIONS.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => selectCounty(option.id)}
                  className={`rounded px-3 py-1.5 text-xs font-semibold transition-colors ${
                    activeCounty === option.id
                      ? 'bg-white text-bcad-700'
                      : 'text-bcad-100 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  {option.short_label}
                </button>
              ))}
            </div>
            <span className="text-xs font-semibold uppercase tracking-wide text-bcad-100 whitespace-nowrap">
              More counties coming
            </span>
          </div>
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

function currentCounty(pathname: string, search: string): CountyId {
  const routeCounty = pathname.match(/^\/property\/(bexar|arapahoe)\//)?.[1]
  if (routeCounty) return normalizeCounty(routeCounty)
  return normalizeCounty(new URLSearchParams(search).get('county') || undefined)
}

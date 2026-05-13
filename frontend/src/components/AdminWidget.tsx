import { useEffect, useState, type FormEvent } from 'react'
import type { User } from 'firebase/auth'
import { fmtMoney } from '../lib/api'
import {
  ADMIN_EMAIL,
  isAdminUser,
  isFirebaseConfigured,
  listLeads,
  signInAdmin,
  signOutAdmin,
  subscribeToAuth,
  type AdminLead,
} from '../lib/firebase'

export default function AdminWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const [email, setEmail] = useState(ADMIN_EMAIL)
  const [password, setPassword] = useState('')
  const [leads, setLeads] = useState<AdminLead[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const configured = isFirebaseConfigured()
  const isAdmin = isAdminUser(user)

  useEffect(() => subscribeToAuth(setUser), [])

  useEffect(() => {
    if (isOpen && isAdmin) {
      void refreshLeads()
    }
  }, [isOpen, isAdmin])

  async function refreshLeads() {
    setLoading(true)
    setError(null)
    try {
      setLeads(await listLeads())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Could not load leads')
    } finally {
      setLoading(false)
    }
  }

  async function handleLogin(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await signInAdmin(email.trim(), password)
      setPassword('')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Could not sign in')
    } finally {
      setLoading(false)
    }
  }

  async function handleSignOut() {
    setError(null)
    await signOutAdmin()
    setLeads([])
  }

  return (
    <div className="fixed bottom-3 right-3 z-50 text-sm">
      {!isOpen && (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="rounded bg-bcad-900/80 px-2 py-1 text-[11px] font-semibold text-white shadow hover:bg-bcad-900"
        >
          Admin
        </button>
      )}

      {isOpen && (
        <section className="w-[min(28rem,calc(100vw-1.5rem))] max-h-[80vh] overflow-y-auto rounded-lg border border-bcad-100 bg-white p-4 text-bcad-900 shadow-xl">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-bcad-700">Admin leads</h2>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="rounded px-2 py-1 text-xs text-bcad-900/60 hover:bg-bcad-50 hover:text-bcad-900"
              aria-label="Close admin panel"
            >
              Close
            </button>
          </div>

          {!configured && (
            <p className="mt-3 rounded bg-amber-50 p-3 text-xs text-amber-900">
              Firebase is not configured in this environment.
            </p>
          )}

          {configured && !user && (
            <form onSubmit={handleLogin} className="mt-3 space-y-3">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-bcad-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-bcad-500"
                autoComplete="username"
              />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                className="w-full rounded-md border border-bcad-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-bcad-500"
                autoComplete="current-password"
              />
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-md bg-bcad-700 px-4 py-2 font-semibold text-white hover:bg-bcad-900 disabled:opacity-50"
              >
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
            </form>
          )}

          {configured && user && !isAdmin && (
            <div className="mt-3 space-y-3">
              <p className="rounded bg-red-50 p-3 text-xs text-red-800">
                This signed-in account is not authorized.
              </p>
              <button
                type="button"
                onClick={handleSignOut}
                className="rounded-md border border-bcad-100 px-3 py-2 text-xs font-semibold text-bcad-700 hover:bg-bcad-50"
              >
                Sign out
              </button>
            </div>
          )}

          {configured && isAdmin && (
            <div className="mt-3">
              <div className="flex items-center justify-between gap-3 border-t border-bcad-100 pt-3">
                <p className="text-xs text-bcad-900/60">{leads.length} recent leads</p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => void refreshLeads()}
                    disabled={loading}
                    className="rounded-md border border-bcad-100 px-3 py-1.5 text-xs font-semibold text-bcad-700 hover:bg-bcad-50 disabled:opacity-50"
                  >
                    Refresh
                  </button>
                  <button
                    type="button"
                    onClick={handleSignOut}
                    className="rounded-md border border-bcad-100 px-3 py-1.5 text-xs font-semibold text-bcad-700 hover:bg-bcad-50"
                  >
                    Sign out
                  </button>
                </div>
              </div>

              {error && <p className="mt-3 rounded bg-red-50 p-3 text-xs text-red-800">{error}</p>}
              {loading && <p className="mt-3 text-xs text-bcad-900/60">Loading leads...</p>}
              {!loading && leads.length === 0 && (
                <p className="mt-3 text-xs text-bcad-900/60">No leads collected yet.</p>
              )}

              <div className="mt-3 space-y-2">
                {leads.map((lead) => (
                  <article key={lead.id} className="rounded-md border border-bcad-100 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-bcad-900">{lead.email}</p>
                        <p className="mt-1 text-xs text-bcad-900/70">
                          {lead.situsAddress || `Property ID ${lead.propertyId}`}
                        </p>
                      </div>
                      <span className="shrink-0 rounded bg-bcad-50 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-bcad-700">
                        {lead.requestType || 'info'}
                      </span>
                    </div>
                    <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-bcad-900/70">
                      <dt>Owner</dt>
                      <dd className="text-right">{lead.owner || 'Unknown'}</dd>
                      <dt>BCAD</dt>
                      <dd className="text-right">{fmtMoney(lead.appraisedValue)}</dd>
                      <dt>Target</dt>
                      <dd className="text-right">{fmtMoney(lead.targetValue)}</dd>
                      <dt>Savings</dt>
                      <dd className="text-right">{fmtMoney(lead.estimatedSavings)}</dd>
                      <dt>Collected</dt>
                      <dd className="text-right">{lead.createdAt || 'Just now'}</dd>
                    </dl>
                  </article>
                ))}
              </div>
            </div>
          )}

          {error && configured && !isAdmin && (
            <p className="mt-3 rounded bg-red-50 p-3 text-xs text-red-800">{error}</p>
          )}
        </section>
      )}
    </div>
  )
}

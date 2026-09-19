import { useCallback, useState } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import {
  ApiError,
  lookUpTicket,
  submitTicket,
  type ResolutionResponse,
  type TicketCategory,
} from './api'

const CATEGORY_LABEL: Record<TicketCategory, string> = {
  billing: 'Billing',
  technical: 'Technical',
  security: 'Security',
}

function initialsOf(name: string | undefined): string {
  if (!name) return '?'
  return name.slice(0, 1).toUpperCase()
}

function Header() {
  const { isAuthenticated, isLoading, user, loginWithRedirect, logout } = useAuth0()

  return (
    <header className="header">
      <div className="brand">
        <div className="brand-mark" aria-hidden="true" />
        <div className="brand-text">
          <span className="brand-name">Triage Desk</span>
          <span className="brand-tag">routed by a real supervisor, not a guess</span>
        </div>
      </div>
      <div className="header-actions">
        {isAuthenticated && (
          <div className="user-chip">
            <span className="avatar">{initialsOf(user?.name ?? user?.email)}</span>
            <span>{user?.email}</span>
          </div>
        )}
        {!isLoading && isAuthenticated && (
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
          >
            Log out
          </button>
        )}
        {!isLoading && !isAuthenticated && (
          <button type="button" className="btn btn-primary" onClick={() => loginWithRedirect()}>
            Sign in
          </button>
        )}
      </div>
    </header>
  )
}

function ResolutionCard({ resolution }: { resolution: ResolutionResponse }) {
  return (
    <div className="card resolution-card">
      <div className="resolution-top">
        <span className="thread-id" title={resolution.ticket_id}>
          {resolution.ticket_id}
        </span>
        <span className={`badge badge-${resolution.handled_by}`}>
          {CATEGORY_LABEL[resolution.handled_by]}
        </span>
      </div>
      {resolution.handoffs.length > 0 && (
        <ul className="handoff-trail">
          {resolution.handoffs.map((handoff, index) => (
            <li key={index}>
              {CATEGORY_LABEL[handoff.from_category]} declined and handed off to{' '}
              {CATEGORY_LABEL[handoff.to_category]}: <em>{handoff.reason}</em>
            </li>
          ))}
        </ul>
      )}
      <p className="resolution-answer">{resolution.answer}</p>
    </div>
  )
}

function SubmitForm({ onResolved }: { onResolved: (resolution: ResolutionResponse) => void }) {
  const { getAccessTokenSilently } = useAuth0()
  const [customerId, setCustomerId] = useState('')
  const [category, setCategory] = useState<TicketCategory>('billing')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault()
      if (!customerId.trim() || !subject.trim() || !body.trim()) return

      setSubmitting(true)
      setError(null)
      try {
        const token = await getAccessTokenSilently()
        if (!token) throw new Error('No access token available.')
        const resolution = await submitTicket(token, {
          ticket_id: `TCK-${Date.now()}`,
          customer_id: customerId.trim(),
          category,
          subject: subject.trim(),
          body: body.trim(),
        })
        onResolved(resolution)
        setSubject('')
        setBody('')
      } catch (err) {
        setError(err instanceof ApiError ? err.problem.detail : 'The ticket could not be sent.')
      } finally {
        setSubmitting(false)
      }
    },
    [customerId, category, subject, body, getAccessTokenSilently, onResolved],
  )

  return (
    <form className="card ticket-form" onSubmit={handleSubmit}>
      <label htmlFor="customer-id">Customer ID</label>
      <input
        id="customer-id"
        type="text"
        placeholder="cust-42"
        value={customerId}
        onChange={(event) => setCustomerId(event.target.value)}
        disabled={submitting}
      />

      <label htmlFor="category">Category</label>
      <select
        id="category"
        value={category}
        onChange={(event) => setCategory(event.target.value as TicketCategory)}
        disabled={submitting}
      >
        <option value="billing">Billing</option>
        <option value="technical">Technical</option>
        <option value="security">Security</option>
      </select>

      <label htmlFor="subject">Subject</label>
      <input
        id="subject"
        type="text"
        placeholder="Invoice looks too high"
        value={subject}
        onChange={(event) => setSubject(event.target.value)}
        disabled={submitting}
      />

      <label htmlFor="body">Body</label>
      <textarea
        id="body"
        rows={4}
        placeholder="Describe the issue..."
        value={body}
        onChange={(event) => setBody(event.target.value)}
        disabled={submitting}
      />

      <button type="submit" className="btn btn-primary" disabled={submitting}>
        {submitting && <span className="spinner" aria-hidden="true" />}
        {submitting ? 'Routing' : 'Submit ticket'}
      </button>
      {error && <p className="form-error">{error}</p>}
    </form>
  )
}

function LookupForm({ onFound }: { onFound: (resolution: ResolutionResponse | null) => void }) {
  const { getAccessTokenSilently } = useAuth0()
  const [ticketId, setTicketId] = useState('')
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault()
      if (!ticketId.trim()) return

      setSearching(true)
      setError(null)
      try {
        const token = await getAccessTokenSilently()
        if (!token) throw new Error('No access token available.')
        const resolution = await lookUpTicket(token, ticketId.trim())
        onFound(resolution)
      } catch (err) {
        setError(err instanceof ApiError ? err.problem.detail : 'The lookup failed.')
      } finally {
        setSearching(false)
      }
    },
    [ticketId, getAccessTokenSilently, onFound],
  )

  return (
    <form className="card lookup-form" onSubmit={handleSubmit}>
      <label htmlFor="ticket-lookup">Look up a ticket's routing history</label>
      <div className="request-row">
        <input
          id="ticket-lookup"
          type="text"
          placeholder="TCK-..."
          value={ticketId}
          onChange={(event) => setTicketId(event.target.value)}
          disabled={searching}
        />
        <button type="submit" className="btn btn-ghost" disabled={searching || !ticketId.trim()}>
          {searching ? 'Looking up' : 'Look up'}
        </button>
      </div>
      {error && <p className="form-error">{error}</p>}
    </form>
  )
}

function Dashboard() {
  const [resolutions, setResolutions] = useState<ResolutionResponse[]>([])
  const [lookupResult, setLookupResult] = useState<ResolutionResponse | null | undefined>(
    undefined,
  )

  const addResolution = useCallback((resolution: ResolutionResponse) => {
    setResolutions((current) => [resolution, ...current])
  }, [])

  return (
    <main className="main">
      <div className="page-heading">
        <h1>Submit a ticket</h1>
        <p>
          Every ticket runs the real supervisor and specialists chapters 19 and 20 already built.
          Nothing here is a mock.
        </p>
      </div>

      <SubmitForm onResolved={addResolution} />
      <LookupForm onFound={setLookupResult} />

      {lookupResult !== undefined && (
        <div className="lookup-result">
          <h2>Lookup result</h2>
          {lookupResult === null ? (
            <p className="queue-empty">No ticket found with that id.</p>
          ) : (
            <ResolutionCard resolution={lookupResult} />
          )}
        </div>
      )}

      <div className="queue-heading">
        <h2>This session</h2>
        <span className="queue-count">
          {resolutions.length} {resolutions.length === 1 ? 'ticket' : 'tickets'}
        </span>
      </div>

      {resolutions.length === 0 ? (
        <div className="queue-empty">Submit a ticket above to see a real routing result.</div>
      ) : (
        <div className="queue">
          {resolutions.map((resolution) => (
            <ResolutionCard key={resolution.ticket_id} resolution={resolution} />
          ))}
        </div>
      )}
    </main>
  )
}

function SignedOutGate() {
  const { loginWithRedirect } = useAuth0()
  return (
    <main className="main">
      <div className="gate">
        <div className="brand-mark" aria-hidden="true" style={{ width: 44, height: 44 }} />
        <h1 className="gate-title">Sign in to triage a ticket</h1>
        <p className="gate-subtitle">
          Every ticket here reaches a real, authenticated API backed by real routing and
          persistence, not a demo stub.
        </p>
        <button type="button" className="btn btn-primary" onClick={() => loginWithRedirect()}>
          Sign in
        </button>
      </div>
    </main>
  )
}

function App() {
  const { isAuthenticated, isLoading } = useAuth0()

  return (
    <div className="shell">
      <Header />
      {isLoading ? null : isAuthenticated ? <Dashboard /> : <SignedOutGate />}
    </div>
  )
}

export default App

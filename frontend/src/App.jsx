import { useState, useEffect, useMemo } from 'react'
import ListingRow from './ListingRow'
import AddRepoModal from './AddRepoModal'
import { ToastContainer, showToast } from './Toast'
import './index.css'

const VIEWS = {
  LIVE:       'live',
  APPROVED:   'approved',
  SKIPPED:    'skipped',
  STATS:      'stats',
}

export default function App() {
  const [view, setView]           = useState(VIEWS.LIVE)
  const [listings, setListings]   = useState([])
  const [approved, setApproved]   = useState([])
  const [skipped, setSkipped]     = useState([])
  const [stats, setStats]         = useState({ total: 0, approved: 0, skipped: 0, pending: 0 })
  const [skills, setSkills]       = useState([])
  const [loading, setLoading]     = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [search, setSearch]       = useState('')
  const [tierFilter, setTierFilter] = useState('all')

  useEffect(() => { loadAll() }, [])

  async function loadAll() {
    setLoading(true)
    try {
      const [listRes, statRes, pipeRes] = await Promise.all([
        fetch('/api/listings'),
        fetch('/api/stats'),
        fetch('/api/pipeline'),
      ])
      const [listData, statData, pipeData] = await Promise.all([
        listRes.json(),
        statRes.json(),
        pipeRes.json(),
      ])
      setListings(listData)
      setStats(statData)
      setApproved(pipeData.approved || [])

      // Pull skipped from DB — we'll reuse pipeline endpoint skipped key
      // For now fetch all seen with a dedicated call
      const skippedRes = await fetch('/api/listings/skipped')
      if (skippedRes.ok) setSkipped(await skippedRes.json())

      // Extract skills from first listing (they all share same user)
      const skillMeta = document.getElementById('user-skills')
      if (skillMeta) {
        try { setSkills(JSON.parse(skillMeta.dataset.skills || '[]')) } catch {}
      }
    } catch {
      showToast('Failed to load data', 'error')
    } finally {
      setLoading(false)
    }
  }

  function handleAction(id) {
    setListings(prev => prev.filter(l => l.id !== id))
    // Refresh stats + pipeline after a moment
    setTimeout(() => {
      fetch('/api/stats').then(r => r.json()).then(setStats)
      fetch('/api/pipeline').then(r => r.json()).then(d => setApproved(d.approved || []))
    }, 400)
  }

  const filteredListings = useMemo(() => {
    return listings.filter(l => {
      if (tierFilter !== 'all') {
        const score = l.match_score
        if (tierFilter === 'strong'  && score < 75) return false
        if (tierFilter === 'good'    && (score < 50 || score >= 75)) return false
        if (tierFilter === 'partial' && (score < 30 || score >= 50)) return false
      }
      if (search) {
        const q = search.toLowerCase()
        if (!l.company?.toLowerCase().includes(q) && !l.role?.toLowerCase().includes(q)) return false
      }
      return true
    })
  }, [listings, tierFilter, search])

  const currentData = view === VIEWS.LIVE
    ? filteredListings
    : view === VIEWS.APPROVED
      ? approved.filter(l => l.company?.toLowerCase().includes(search.toLowerCase()) || l.role?.toLowerCase().includes(search.toLowerCase()))
      : view === VIEWS.SKIPPED
        ? skipped.filter(l => l.company?.toLowerCase().includes(search.toLowerCase()) || l.role?.toLowerCase().includes(search.toLowerCase()))
        : []

  const viewMeta = {
    [VIEWS.LIVE]:     { title: 'Live Pipeline', sub: 'New listings scored against your resume — approve or skip each one.' },
    [VIEWS.APPROVED]: { title: 'Approved Listings', sub: 'Roles you\'ve approved and pushed to your Google Sheet.' },
    [VIEWS.SKIPPED]:  { title: 'Skipped Listings', sub: 'Roles you\'ve dismissed — they won\'t appear again.' },
    [VIEWS.STATS]:    { title: 'Statistics', sub: 'Overview of your pipeline activity and extracted skills.' },
  }

  return (
    <>
      <div className="app-shell">

        {/* ── Top Bar ── */}
        <header className="topbar">
          <div className="topbar-brand">
            <span className="brand-name">InternshipScraper</span>
          </div>
          <nav className="topbar-nav">
            <button
              className={`topbar-tab ${view === VIEWS.LIVE ? 'active' : ''}`}
              onClick={() => setView(VIEWS.LIVE)}
            >
              Dashboard
            </button>
            <button
              className={`topbar-tab ${view === VIEWS.APPROVED || view === VIEWS.SKIPPED ? 'active' : ''}`}
              onClick={() => setView(VIEWS.APPROVED)}
            >
              History
            </button>
            <button
              className={`topbar-tab ${view === VIEWS.STATS ? 'active' : ''}`}
              onClick={() => setView(VIEWS.STATS)}
            >
              Analytics
            </button>
          </nav>
          <div className="topbar-actions">
            <button id="refresh-btn" className="btn btn-outline" onClick={loadAll}>
              ↻ Refresh
            </button>
            <button id="add-repo-btn" className="btn btn-orange" onClick={() => setShowModal(true)}>
              + Add Repo
            </button>
          </div>
        </header>

        {/* ── Sidebar ── */}
        <aside className="sidebar">
          <div className="sidebar-sync">
            <button className="btn btn-orange" onClick={loadAll}>Sync Repos</button>
          </div>

          <div className="sidebar-section-label">Pipeline</div>
          <button
            className={`nav-item ${view === VIEWS.LIVE ? 'active' : ''}`}
            onClick={() => setView(VIEWS.LIVE)}
          >
            <span className="nav-icon">🚀</span>
            Live Pipeline
            {listings.length > 0 && (
              <span className="nav-badge">{listings.length}</span>
            )}
          </button>
          <button
            className={`nav-item ${view === VIEWS.APPROVED ? 'active' : ''}`}
            onClick={() => setView(VIEWS.APPROVED)}
          >
            <span className="nav-icon">✓</span>
            Approved
            {stats.approved > 0 && (
              <span className="nav-badge">{stats.approved}</span>
            )}
          </button>
          <button
            className={`nav-item ${view === VIEWS.SKIPPED ? 'active' : ''}`}
            onClick={() => setView(VIEWS.SKIPPED)}
          >
            <span className="nav-icon">✕</span>
            Skipped
          </button>

          <div className="sidebar-divider" />

          <button
            className={`nav-item ${view === VIEWS.STATS ? 'active' : ''}`}
            onClick={() => setView(VIEWS.STATS)}
          >
            <span className="nav-icon">📊</span>
            Statistics
          </button>

          <div className="sidebar-footer">
            <div className="nav-item" style={{ cursor: 'default', fontSize: '0.72rem', color: 'var(--muted)' }}>
              V1.0 Active
            </div>
          </div>
        </aside>

        {/* ── Main Content ── */}
        <main className="main-content">
          {view === VIEWS.STATS ? (
            <>
              <div className="content-header">
                <div>
                  <div className="content-title">{viewMeta[view].title}</div>
                  <div className="content-subtitle">{viewMeta[view].sub}</div>
                </div>
              </div>
              <div className="stats-page">
                <div className="stats-grid">
                  <div className="stat-card total">
                    <div className="stat-val">{stats.total}</div>
                    <div className="stat-lbl">Total Seen</div>
                  </div>
                  <div className="stat-card approved">
                    <div className="stat-val">{stats.approved}</div>
                    <div className="stat-lbl">Approved</div>
                  </div>
                  <div className="stat-card skipped">
                    <div className="stat-val">{stats.skipped}</div>
                    <div className="stat-lbl">Skipped</div>
                  </div>
                  <div className="stat-card pending">
                    <div className="stat-val">{stats.pending}</div>
                    <div className="stat-lbl">Pending Review</div>
                  </div>
                </div>
                {skills.length > 0 && (
                  <div className="skills-card">
                    <h3>Your Extracted Skills</h3>
                    <div className="skills-list">
                      {skills.map(s => <span key={s} className="skill-pill">{s}</span>)}
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <div className="content-header">
                <div>
                  <div className="content-title">{viewMeta[view].title}</div>
                  <div className="content-subtitle">{viewMeta[view].sub}</div>
                </div>
                <div className="content-tools">
                  <div className="search-box">
                    <span className="search-icon">🔍</span>
                    <input
                      id="search-input"
                      type="text"
                      placeholder="Search roles or companies…"
                      value={search}
                      onChange={e => setSearch(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {view === VIEWS.LIVE && (
                <div className="filter-strip">
                  <select
                    id="tier-filter"
                    value={tierFilter}
                    onChange={e => setTierFilter(e.target.value)}
                  >
                    <option value="all">All Tiers</option>
                    <option value="strong">🔥 Strong (75+)</option>
                    <option value="good">✅ Good (50–74)</option>
                    <option value="partial">🟡 Partial (30–49)</option>
                  </select>
                  <span className="filter-count">{filteredListings.length} listings</span>
                </div>
              )}

              {loading ? (
                <div className="state-center">
                  <div className="spinner" />
                  <span style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>Loading…</span>
                </div>
              ) : currentData.length === 0 ? (
                <div className="state-center">
                  <div className="state-icon">
                    {view === VIEWS.LIVE ? '🎉' : view === VIEWS.APPROVED ? '📋' : '🗂️'}
                  </div>
                  <div className="state-title">
                    {view === VIEWS.LIVE
                      ? "You're all caught up"
                      : view === VIEWS.APPROVED
                        ? 'No approved listings yet'
                        : 'No skipped listings'}
                  </div>
                  <div className="state-sub">
                    {view === VIEWS.LIVE
                      ? 'All listings reviewed. Add a new repo or come back tomorrow.'
                      : 'Approve listings from the Live Pipeline to see them here.'}
                  </div>
                </div>
              ) : (
                <div className="table-wrap">
                  <table className="listing-table">
                    <thead>
                      <tr>
                        <th>Company</th>
                        <th>Role</th>
                        <th>Location</th>
                        <th>Match Score</th>
                        <th>{view === VIEWS.LIVE ? 'Posted' : 'Date Approved'}</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentData.map(l => (
                        <ListingRow
                          key={l.id}
                          listing={l}
                          onAction={handleAction}
                          showActions={view === VIEWS.LIVE}
                        />
                      ))}
                    </tbody>
                  </table>
                  <div className="table-footer">
                    Showing {currentData.length} {view === VIEWS.LIVE ? 'new' : view} listing{currentData.length !== 1 ? 's' : ''}
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>

      {showModal && (
        <AddRepoModal onClose={() => setShowModal(false)} onAdded={loadAll} />
      )}
      <ToastContainer />
      <div id="user-skills" data-skills="[]" style={{ display: 'none' }} />
    </>
  )
}

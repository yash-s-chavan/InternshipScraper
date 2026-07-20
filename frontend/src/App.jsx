import { useState, useEffect, useMemo } from 'react'
import ListingCard from './ListingCard'
import RightPanel from './RightPanel'
import AddRepoModal from './AddRepoModal'
import { ToastContainer, showToast } from './Toast'
import './index.css'

const TIERS = ['All Tiers', '🔥 Strong', '✅ Good', '🟡 Partial', '⚪ Speculative']

export default function App() {
  const [listings, setListings]     = useState([])
  const [stats, setStats]           = useState({ total: 0, approved: 0, skipped: 0, pending: 0 })
  const [skills, setSkills]         = useState([])
  const [loading, setLoading]       = useState(true)
  const [showModal, setShowModal]   = useState(false)

  // Filters
  const [tierFilter, setTierFilter]       = useState('All Tiers')
  const [locationFilter, setLocationFilter] = useState('all')
  const [search, setSearch]               = useState('')

  useEffect(() => {
    loadAll()
  }, [])

  async function loadAll() {
    setLoading(true)
    try {
      const [listRes, statRes] = await Promise.all([
        fetch('/api/listings'),
        fetch('/api/stats'),
      ])
      const listData = await listRes.json()
      const statData = await statRes.json()
      setListings(listData)
      setStats(statData)

      // Extract skills from first listing's source data (passed via Flask template vars)
      // We read them from a meta tag injected by Flask
      const skillMeta = document.getElementById('user-skills')
      if (skillMeta) {
        try { setSkills(JSON.parse(skillMeta.dataset.skills || '[]')) } catch { /* skip */ }
      }
    } catch {
      showToast('Failed to load listings', 'error')
    } finally {
      setLoading(false)
    }
  }

  function handleAction(id) {
    setListings(prev => prev.filter(l => l.id !== id))
    setStats(prev => ({ ...prev, pending: Math.max(0, prev.pending - 1) }))
  }

  const filtered = useMemo(() => {
    return listings.filter(l => {
      if (tierFilter !== 'All Tiers' && !l.match_tier?.includes(tierFilter.replace(/[🔥✅🟡⚪]\s*/g, ''))) return false
      if (locationFilter === 'preferred') {
        const preferred = ['philadelphia','pa','bellevue','wa','seattle','dallas','tx','remote','new york','ny','san francisco','ca']
        if (!preferred.some(p => l.location?.toLowerCase().includes(p))) return false
      }
      if (search) {
        const q = search.toLowerCase()
        if (!l.company?.toLowerCase().includes(q) && !l.role?.toLowerCase().includes(q)) return false
      }
      return true
    })
  }, [listings, tierFilter, locationFilter, search])

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric'
  })

  return (
    <>
      {/* ── Header ── */}
      <header className="header">
        <div className="header-brand">
          <span className="logo">🚀</span>
          <span className="brand-name">Internship</span>
          <span className="brand-accent">Scraper</span>
        </div>
        <span className="header-date">{today}</span>

        <div className="header-stats">
          <div className="stat-pill">
            <strong>{listings.length}</strong> new
          </div>
          <div className="stat-pill approved">
            <strong>{stats.approved}</strong> approved
          </div>
          <div className="stat-pill skipped">
            <strong>{stats.skipped}</strong> skipped
          </div>
        </div>

        <div className="header-actions">
          <button
            id="add-repo-btn"
            className="btn btn-ghost"
            onClick={() => setShowModal(true)}
          >
            ＋ Add Repo
          </button>
          <button
            id="rescrape-btn"
            className="btn btn-primary"
            onClick={loadAll}
          >
            ↻ Refresh
          </button>
        </div>
      </header>

      {/* ── Main Layout ── */}
      <div className="layout">

        {/* Left: Listings Panel */}
        <section className="listings-panel">
          <div className="filter-bar">
            <span className="filter-label">Filter:</span>
            <input
              id="search-input"
              type="text"
              placeholder="Search company or role…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <select
              id="tier-filter"
              value={tierFilter}
              onChange={e => setTierFilter(e.target.value)}
            >
              {TIERS.map(t => <option key={t}>{t}</option>)}
            </select>
            <select
              id="location-filter"
              value={locationFilter}
              onChange={e => setLocationFilter(e.target.value)}
            >
              <option value="all">All Locations</option>
              <option value="preferred">Preferred Only</option>
            </select>
            <span className="filter-count">{filtered.length} listings</span>
          </div>

          {loading ? (
            <div className="loading-state">
              <div className="spinner" />
              <span>Loading listings…</span>
            </div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🎉</div>
              <h3>{listings.length === 0 ? "You're all caught up!" : "No matches for those filters"}</h3>
              <p>
                {listings.length === 0
                  ? "All listings have been reviewed. Check back tomorrow or add a new repo."
                  : "Try broadening your search or filter criteria."}
              </p>
            </div>
          ) : (
            <div className="listings-scroll">
              {filtered.map((l, i) => (
                <div key={l.id} style={{ animationDelay: `${Math.min(i * 40, 400)}ms` }}>
                  <ListingCard listing={l} onAction={handleAction} />
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Right: Pipeline + Stats */}
        <RightPanel skills={skills} />
      </div>

      {/* ── Add Repo Modal ── */}
      {showModal && (
        <AddRepoModal
          onClose={() => setShowModal(false)}
          onAdded={loadAll}
        />
      )}

      {/* ── Toasts ── */}
      <ToastContainer />

      {/* Skills meta tag (populated by Flask) */}
      <div id="user-skills" data-skills="[]" style={{ display: 'none' }} />
    </>
  )
}

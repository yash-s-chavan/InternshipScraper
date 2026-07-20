import { useState, useEffect } from 'react'

export default function RightPanel({ skills }) {
  const [tab, setTab] = useState('pipeline')
  const [approved, setApproved] = useState([])
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetchPipeline()
    fetchStats()
  }, [])

  async function fetchPipeline() {
    try {
      const res = await fetch('/api/pipeline')
      const data = await res.json()
      setApproved(data.approved || [])
    } catch { /* silent */ }
  }

  async function fetchStats() {
    try {
      const res = await fetch('/api/stats')
      setStats(await res.json())
    } catch { /* silent */ }
  }

  return (
    <div className="right-panel">
      <div className="panel-tabs">
        <button
          id="tab-pipeline"
          className={`tab-btn ${tab === 'pipeline' ? 'active' : ''}`}
          onClick={() => { setTab('pipeline'); fetchPipeline() }}
        >
          📋 Pipeline {approved.length > 0 && `(${approved.length})`}
        </button>
        <button
          id="tab-stats"
          className={`tab-btn ${tab === 'stats' ? 'active' : ''}`}
          onClick={() => { setTab('stats'); fetchStats() }}
        >
          📊 Stats
        </button>
      </div>

      <div className="panel-content">
        {tab === 'pipeline' && (
          approved.length === 0
            ? <p className="pipeline-empty">No approved listings yet.<br/>Hit ✅ on a card to add one.</p>
            : approved.map(l => (
              <div key={l.id} className="pipeline-item">
                <div className="pipeline-company">{l.company}</div>
                <div className="pipeline-role">{l.role}</div>
                <div className="pipeline-meta">
                  <span className="pipeline-score">⚡ {l.match_score}</span>
                  {l.location && <span style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>📍 {l.location}</span>}
                  {l.link && <a href={l.link} target="_blank" rel="noreferrer" className="pipeline-link">Apply ↗</a>}
                  <span className="pipeline-date">{l.actioned_at?.slice(0, 10)}</span>
                </div>
              </div>
            ))
        )}

        {tab === 'stats' && stats && (
          <>
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
                <div className="stat-lbl">Pending</div>
              </div>
            </div>

            {skills?.length > 0 && (
              <div className="skills-section">
                <h4>Your Skills</h4>
                <div className="skills-list">
                  {skills.map(s => (
                    <span key={s} className="skill-chip matched">{s}</span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

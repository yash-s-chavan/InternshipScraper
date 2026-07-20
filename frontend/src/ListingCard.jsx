import { useState } from 'react'
import { showToast } from './Toast'

const PREFERRED_LOCATIONS = [
  'philadelphia', 'pa', 'bellevue', 'wa', 'seattle',
  'dallas', 'tx', 'remote', 'new york', 'ny', 'san francisco', 'ca',
]

function isPreferred(location) {
  if (!location) return false
  const loc = location.toLowerCase()
  return PREFERRED_LOCATIONS.some(p => loc.includes(p))
}

function tierClass(tier) {
  if (tier.includes('Strong')) return 'tier-strong'
  if (tier.includes('Good'))   return 'tier-good'
  if (tier.includes('Partial'))return 'tier-partial'
  return 'tier-spec'
}

export default function ListingCard({ listing, onAction }) {
  const [busy, setBusy] = useState(false)
  const [removing, setRemoving] = useState(false)

  async function handleAction(type) {
    if (busy) return
    setBusy(true)

    try {
      const res = await fetch(`/api/${type}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: listing.id }),
      })
      const data = await res.json()

      if (!res.ok) {
        showToast(data.error || 'Something went wrong', 'error')
        setBusy(false)
        return
      }

      if (type === 'approve') {
        showToast(
          data.sheets_pushed
            ? `✨ ${listing.company} added to your Sheet`
            : `✅ Approved — Sheets not configured`,
          'success'
        )
      } else {
        showToast(`Skipped ${listing.company}`, 'info')
      }

      setRemoving(true)
      setTimeout(() => onAction(listing.id), 320)
    } catch {
      showToast('Network error', 'error')
      setBusy(false)
    }
  }

  return (
    <div
      className={`card ${removing ? 'removing' : ''}`}
      onMouseMove={e => {
        const rect = e.currentTarget.getBoundingClientRect()
        e.currentTarget.style.setProperty('--mx', `${e.clientX - rect.left}px`)
        e.currentTarget.style.setProperty('--my', `${e.clientY - rect.top}px`)
      }}
    >
      <div className="card-top">
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="card-company">{listing.company}</div>
          <div className="card-role">{listing.role}</div>
        </div>
        <div className={`score-badge ${tierClass(listing.match_tier)}`}>
          <span className="score-num">{listing.match_score}</span>
          <span className="score-tier">
            {listing.match_tier.replace(/[🔥✅🟡⚪]\s*/g, '')}
          </span>
        </div>
      </div>

      <div className="card-meta">
        {listing.location && (
          <span className={`meta-tag ${isPreferred(listing.location) ? 'preferred' : ''}`}>
            📍 {listing.location}
          </span>
        )}
        {listing.salary && (
          <span className="meta-tag">💰 {listing.salary}</span>
        )}
        {listing.date_posted && (
          <span className="meta-tag">🕐 {listing.date_posted}</span>
        )}
      </div>

      {listing.skills_matched?.length > 0 && (
        <div className="skills-row">
          {listing.skills_matched.map(s => (
            <span key={s} className="skill-chip matched">{s}</span>
          ))}
        </div>
      )}

      <div className="card-actions">
        <button
          id={`approve-${listing.id}`}
          className="btn btn-approve"
          onClick={() => handleAction('approve')}
          disabled={busy}
        >
          ✅ Add to Sheet
        </button>
        <button
          id={`skip-${listing.id}`}
          className="btn btn-skip"
          onClick={() => handleAction('skip')}
          disabled={busy}
        >
          ❌ Skip
        </button>
        {listing.link && (
          <a
            href={listing.link}
            target="_blank"
            rel="noreferrer"
            className="btn-apply"
          >
            Apply ↗
          </a>
        )}
        <span className="source-tag">{listing.source}</span>
      </div>
    </div>
  )
}

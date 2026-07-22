import { useState } from 'react'
import { showToast } from './Toast'

const PREFERRED = ['philadelphia','pa','bellevue','wa','seattle','dallas','tx','remote','new york','ny','san francisco','ca']

function isPreferred(loc) {
  if (!loc) return false
  const l = loc.toLowerCase()
  return PREFERRED.some(p => l.includes(p))
}

function scoreClass(score) {
  if (score >= 75) return 'score-strong'
  if (score >= 50) return 'score-good'
  if (score >= 30) return 'score-partial'
  return 'score-spec'
}

function initials(company) {
  return (company || '?').trim()[0].toUpperCase()
}

export default function ListingRow({ listing, onAction, showActions = true }) {
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
      if (!res.ok) { showToast(data.error || 'Error', 'error'); setBusy(false); return }

      if (type === 'approve') {
        showToast(
          data.sheets_pushed
            ? `${listing.company} added to your Sheet`
            : `Approved — configure Sheets to sync`,
          'success'
        )
      } else {
        showToast(`Skipped ${listing.company}`, 'info')
      }

      setRemoving(true)
      setTimeout(() => onAction(listing.id), 280)
    } catch {
      showToast('Network error', 'error')
      setBusy(false)
    }
  }

  const preferred = isPreferred(listing.location)

  return (
    <tr className={removing ? 'removing' : ''}>
      {/* Company */}
      <td>
        <div className="company-cell">
          <div className="avatar">{initials(listing.company)}</div>
          <div>
            <div className="company-name">{listing.company}</div>
            <div className="company-source">{listing.source}</div>
          </div>
        </div>
      </td>

      {/* Role */}
      <td>
        <div className="role-cell">
          <div className="role-title">{listing.role}</div>
          {listing.skills_matched?.length > 0 && (
            <div className="role-skills">
              {listing.skills_matched.slice(0, 4).map(s => (
                <span key={s} className="skill-tag">{s}</span>
              ))}
              {listing.skills_matched.length > 4 && (
                <span className="skill-tag">+{listing.skills_matched.length - 4}</span>
              )}
            </div>
          )}
        </div>
      </td>

      {/* Location */}
      <td>
        <div className="location-cell">
          <span className={preferred ? 'preferred' : ''}>
            {listing.location || '—'}
          </span>
        </div>
      </td>

      {/* Score */}
      <td>
        <span className={`score-badge ${scoreClass(listing.match_score)}`}>
          {listing.match_score}%
        </span>
      </td>

      {/* Date */}
      <td style={{ color: 'var(--text-2)', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
        {listing.date_posted || listing.actioned_at?.slice(0, 10) || '—'}
      </td>

      {/* Actions */}
      <td>
        <div className="action-cell">
          {listing.link && (
            <a href={listing.link} target="_blank" rel="noreferrer" className="btn-apply-link">
              Apply ↗
            </a>
          )}
          {showActions && (
            <>
              <button
                id={`approve-${listing.id}`}
                className="btn-approve"
                onClick={() => handleAction('approve')}
                disabled={busy}
              >
                Add
              </button>
              <button
                id={`skip-${listing.id}`}
                className="btn-skip"
                onClick={() => handleAction('skip')}
                disabled={busy}
              >
                Skip
              </button>
            </>
          )}
        </div>
      </td>
    </tr>
  )
}

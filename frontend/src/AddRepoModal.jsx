import { useState } from 'react'
import { showToast } from './Toast'

export default function AddRepoModal({ onClose, onAdded }) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!url.trim()) return

    setLoading(true)
    try {
      const res = await fetch('/api/add-repo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      })
      const data = await res.json()
      if (!res.ok) {
        showToast(data.error || 'Failed to add repo', 'error')
      } else {
        showToast(`Repo added — ${data.new_count} new listings found`, 'success')
        onAdded()
        onClose()
      }
    } catch {
      showToast('Network error', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <h2>➕ Add Repo</h2>
        <p>Paste any GitHub internship repo URL and we'll scrape + score it immediately.</p>
        <form onSubmit={handleSubmit}>
          <input
            id="add-repo-input"
            type="url"
            placeholder="https://github.com/owner/repo"
            value={url}
            onChange={e => setUrl(e.target.value)}
            autoFocus
          />
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading || !url.trim()}>
              {loading ? 'Scraping…' : 'Add Repo'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

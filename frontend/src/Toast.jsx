import { useState, useCallback } from 'react'

let _setToasts = null

export function ToastContainer() {
  const [items, setItems] = useState([])
  _setToasts = setItems

  return (
    <div className="toast-container">
      {items.map(t => (
        <div key={t.id} className={`toast ${t.type}`}>
          <span>{t.icon}</span>
          <span>{t.message}</span>
        </div>
      ))}
    </div>
  )
}

export function showToast(message, type = 'info') {
  const icons = { success: '✓', error: '✕', info: '→' }
  const id = Date.now()
  if (_setToasts) {
    _setToasts(prev => [...prev, { id, message, type, icon: icons[type] }])
    setTimeout(() => _setToasts(prev => prev.filter(t => t.id !== id)), 3000)
  }
}

import { useState, useCallback } from 'react'

const toasts = []
let setToastsGlobal = null

export function ToastContainer() {
  const [items, setItems] = useState([])
  setToastsGlobal = setItems

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
  const icons = { success: '✅', error: '❌', info: 'ℹ️' }
  const id = Date.now()
  const toast = { id, message, type, icon: icons[type] }

  if (setToastsGlobal) {
    setToastsGlobal(prev => [...prev, toast])
    setTimeout(() => {
      setToastsGlobal(prev => prev.filter(t => t.id !== id))
    }, 3200)
  }
}

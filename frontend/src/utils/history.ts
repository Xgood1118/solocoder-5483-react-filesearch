import type { HistoryItem } from '@/types'

const KEY = 'fs_search_history'
const MAX = 50

export function loadHistory(): HistoryItem[] {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return []
    const arr = JSON.parse(raw) as HistoryItem[]
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

export function pushHistory(q: string) {
  if (!q || !q.trim()) return
  const clean = q.trim()
  const list = loadHistory().filter(x => x.q !== clean)
  list.unshift({ q: clean, at: Date.now() })
  const kept = list.slice(0, MAX)
  try {
    localStorage.setItem(KEY, JSON.stringify(kept))
  } catch {}
}

export function clearHistory() {
  try {
    localStorage.removeItem(KEY)
  } catch {}
}

export function removeHistoryItem(q: string) {
  const list = loadHistory().filter(x => x.q !== q)
  try {
    localStorage.setItem(KEY, JSON.stringify(list))
  } catch {}
}

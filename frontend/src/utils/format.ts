export function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let v = n
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v.toFixed(v >= 100 || i === 0 ? 0 : 1)} ${units[i]}`
}

export function formatDate(ts: number | string | undefined | null): string {
  if (!ts) return '-'
  const t = typeof ts === 'number' ? ts * 1000 : new Date(ts).getTime()
  if (Number.isNaN(t)) return '-'
  const d = new Date(t)
  const pad = (x: number) => x.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function basename(p: string): string {
  if (!p) return ''
  const i = Math.max(p.lastIndexOf('/'), p.lastIndexOf('\\'))
  return i >= 0 ? p.slice(i + 1) : p
}

export function dirname(p: string): string {
  if (!p) return ''
  const i = Math.max(p.lastIndexOf('/'), p.lastIndexOf('\\'))
  return i >= 0 ? p.slice(0, i) : p
}

export function fileIcon(ext: string, mime: string): string {
  const e = (ext || '').toLowerCase()
  if (e === 'pdf') return '📄'
  if (['doc', 'docx'].includes(e)) return '📝'
  if (['ppt', 'pptx'].includes(e)) return '📊'
  if (['xls', 'xlsx', 'csv'].includes(e)) return '📈'
  if (['txt', 'md'].includes(e)) return '📃'
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'].includes(e)) return '🖼️'
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(e)) return '🗜️'
  if (['py', 'js', 'ts', 'tsx', 'jsx', 'java', 'c', 'cpp', 'go', 'rs', 'rb', 'sh'].includes(e)) return '💻'
  if (mime?.startsWith('image/')) return '🖼️'
  if (mime?.startsWith('text/')) return '📃'
  return '📁'
}

const DANGEROUS_ATTR = /\s(on\w+|style)\s*=/gi
export function sanitizeHighlightHtml(html: string): string {
  if (!html) return ''
  let out = html
  out = out.replace(DANGEROUS_ATTR, ' data-removed=')
  out = out.replace(/javascript\s*:/gi, 'data-invalid:')
  return out
}

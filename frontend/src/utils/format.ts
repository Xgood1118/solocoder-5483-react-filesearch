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

// Whitelist of HTML event-handler attribute names. Used as a fallback pass to
// catch attributes that the broader regex misses (e.g. when `on` is glued
// directly to an alphanumeric attribute value like `<img src=xonerror=...>`).
// Using a whitelist (rather than the catch-all `on\w+`) avoids stripping
// legitimate text like "one=1" / "only=the" / "longitude=42" which happen to
// start with "on".
const EVENT_ATTRS = [
  'onload', 'onerror', 'onclick', 'ondblclick', 'onmousedown', 'onmouseup',
  'onmouseover', 'onmousemove', 'onmouseout', 'onmouseenter', 'onmouseleave',
  'onkeydown', 'onkeyup', 'onkeypress', 'onfocus', 'onblur', 'onchange',
  'oninput', 'onsubmit', 'onreset', 'onselect', 'onabort', 'onresize',
  'onscroll', 'onunload', 'onbeforeunload', 'oncopy', 'oncut', 'onpaste',
  'ondrag', 'ondragstart', 'ondragend', 'ondragover', 'ondragleave',
  'ondrop', 'ontouchstart', 'ontouchend', 'ontouchmove', 'onpointerdown',
  'onpointerup', 'onpointermove', 'onwheel', 'oncontextmenu', 'onstorage',
  'onmessage', 'onpopstate', 'onhashchange', 'onanimationstart',
  'onanimationend', 'onanimationiteration', 'ontransitionend',
]
const EVENT_ATTR_RE = new RegExp(
  `(?:${EVENT_ATTRS.join('|')})\\s*=`,
  'gi',
)
// Anchor must be a character that can plausibly start an HTML attribute inside
// a tag: whitespace, attribute delimiter, or another attribute boundary. We
// intentionally do NOT include `>` because `>` closes a tag and content after
// it is plain text (so `<p>one=1 two=2</p>` is not an attribute context).
// This catches `<tag onerror=...>` (space), `<tag/onerror=...>` (slash — the
// previous sanitizer missed this), `<tag a=b/onerror=...>`, etc.
const DANGEROUS_ATTR = /[\s/"'=](?:on\w+|style)\s*=/gi
export function sanitizeHighlightHtml(html: string): string {
  if (!html) return ''
  let out = html
  // First pass: catch the common "<tag attr onerror=...>" form.
  out = out.replace(DANGEROUS_ATTR, ' data-removed=')
  // Second pass: catch event-handler attributes that survived because they
  // appear right after a tag-closing `>` or alphanumeric boundary. The
  // whitelist is exact so we don't false-positive on words like "one=".
  out = out.replace(EVENT_ATTR_RE, 'data-removed=')
  out = out.replace(/javascript\s*:/gi, 'data-invalid:')
  return out
}

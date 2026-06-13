import type { SearchHit } from '@/types'
import { formatBytes, formatDate, fileIcon, sanitizeHighlightHtml, dirname } from '@/utils/format'
import './ResultCard.css'

interface Props {
  hit: SearchHit
  onClick: () => void
}

export default function ResultCard({ hit, onClick }: Props) {
  return (
    <article className="result-card" onClick={onClick}>
      <div className="rc-main">
        <div className="rc-head">
          <span className="rc-icon" aria-hidden>{fileIcon(hit.ext, hit.mime_type)}</span>
          <h3 className="rc-name" dangerouslySetInnerHTML={{ __html: sanitizeHighlightHtml(highlightName(hit)) }} />
          <div className="rc-meta-right">
            <span className="rc-score" title={`BM25 分: ${hit.bm25_score}`}>相关度 {hit.score}</span>
          </div>
        </div>
        <div className="rc-path" title={hit.path}>
          <span className="rc-dir">{dirname(hit.path)}</span>
          <span className="rc-slash">/</span>
          <span className="rc-fname">{hit.name}</span>
        </div>
        {hit.snippet_html && (
          <div
            className="rc-snippet"
            dangerouslySetInnerHTML={{ __html: sanitizeHighlightHtml(hit.snippet_html) }}
          />
        )}
        <div className="rc-meta">
          <span title="大小">{formatBytes(hit.size)}</span>
          <span className="dot">·</span>
          <span title="修改时间">{formatDate(hit.mtime)}</span>
          <span className="dot">·</span>
          <span title="MIME">{hit.ext || hit.mime_type.split('/')[1] || 'file'}</span>
          {hit.owner && (
            <>
              <span className="dot">·</span>
              <span title="所有者">{hit.owner}</span>
            </>
          )}
          {hit.tags?.length > 0 && (
            <>
              <span className="dot">·</span>
              <span className="rc-tags">
                {hit.tags.map((t, i) => (
                  <span key={i} className="rc-tag">#{t}</span>
                ))}
              </span>
            </>
          )}
          {hit.ocr_low_conf && (
            <>
              <span className="dot">·</span>
              <span className="ocr-warn" title="该页为 OCR 识别，置信度低，文字可能有误">⚠️ OCR 低置信</span>
            </>
          )}
        </div>
      </div>
    </article>
  )
}

function highlightName(hit: SearchHit): string {
  const h = hit.snippet_plain || ''
  const name = escapeHtml(hit.name)
  if (!h) return name
  return name
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

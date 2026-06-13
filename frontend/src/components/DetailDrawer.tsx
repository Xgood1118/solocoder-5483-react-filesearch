import { useEffect, useState } from 'react'
import type { SearchHit, FileDetail, RelatedFiles, FileMeta } from '@/types'
import { API } from '@/utils/api'
import { formatBytes, formatDate, fileIcon, sanitizeHighlightHtml } from '@/utils/format'
import './DetailDrawer.css'

interface Props {
  hit: SearchHit | null
  onClose: () => void
}

export default function DetailDrawer({ hit, onClose }: Props) {
  const [detail, setDetail] = useState<FileDetail | null>(null)
  const [related, setRelated] = useState<RelatedFiles | null>(null)
  const [tab, setTab] = useState<'preview' | 'related' | 'raw'>('preview')
  const open = !!hit

  useEffect(() => {
    if (!hit) {
      setDetail(null)
      setRelated(null)
      setTab('preview')
      return
    }
    let alive = true
    const run = async () => {
      try {
        const [dr, rr] = await Promise.all([
          API.fileDetail(hit.file_id),
          API.fileRelated(hit.file_id, 5),
        ])
        if (!alive) return
        setDetail(dr.data as FileDetail)
        setRelated(rr.data as RelatedFiles)
      } catch (e) {
        if (alive) setDetail(null)
      }
    }
    run()
    return () => { alive = false }
  }, [hit?.file_id])

  const renderPreview = () => {
    if (!detail) return <div className="placeholder">加载中…</div>
    const mime = detail.mime_type || ''
    const url = API.fileContent(detail.file_id)
    if (mime === 'application/pdf') {
      return (
        <div className="pdf-view">
          <iframe
            title={detail.name}
            src={url}
            style={{ width: '100%', height: '70vh', border: '1px solid var(--border)', borderRadius: 8 }}
          />
        </div>
      )
    }
    if (mime.startsWith('image/')) {
      return (
        <div className="img-view">
          <img src={url} alt={detail.name} />
          {detail.ocr_low_conf && (
            <div className="ocr-note">⚠️ 该内容来自 OCR 识别，置信度低，文字可能有误</div>
          )}
        </div>
      )
    }
    if (mime.startsWith('text/') || ['py', 'js', 'ts', 'tsx', 'jsx', 'md', 'txt', 'json', 'yaml', 'yml', 'html', 'css'].includes(detail.ext || '')) {
      return (
        <div className="text-view">
          <pre>{detail.content_preview}</pre>
        </div>
      )
    }
    return (
      <div className="placeholder">
        <p>无法预览此类型文件，请下载后查看。</p>
        <a className="btn primary" href={url} download>下载文件</a>
      </div>
    )
  }

  const renderRelated = () => {
    if (!related) return <div className="placeholder">加载中…</div>
    return (
      <div className="related-grid">
        <RelatedGroup title="同目录文件" items={related.same_dir} onClose={onClose} />
        <RelatedGroup title="同标签文件" items={related.same_tags} onClose={onClose} />
        <RelatedGroup title="同 Owner 最近文件" items={related.same_owner} onClose={onClose} />
      </div>
    )
  }

  const renderRaw = () => {
    if (!detail) return <div className="placeholder">加载中…</div>
    return (
      <div className="raw-view">
        <pre
          dangerouslySetInnerHTML={{
            __html: sanitizeHighlightHtml(
              detail.content_preview
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
            ),
          }}
        />
      </div>
    )
  }

  return (
    <div className={'drawer-backdrop' + (open ? ' open' : '')} onClick={onClose}>
      <div
        className={'drawer' + (open ? ' open' : '')}
        onClick={e => e.stopPropagation()}
      >
        <header className="drawer-head">
          <div className="drawer-title">
            <span className="drawer-icon">{hit ? fileIcon(hit.ext, hit.mime_type) : ''}</span>
            <div>
              <h2>{hit?.name || '详情'}</h2>
              <div className="drawer-path">{hit?.path}</div>
            </div>
          </div>
          <button className="closebtn" onClick={onClose}>×</button>
        </header>

        {detail && (
          <div className="drawer-meta">
            <Meta label="大小" value={formatBytes(detail.size)} />
            <Meta label="修改时间" value={formatDate(detail.mtime)} />
            <Meta label="类型" value={detail.ext?.toUpperCase() || detail.mime_type} />
            <Meta label="所有者" value={detail.owner || '-'} />
            {detail.tags?.length > 0 && (
              <Meta label="标签" value={detail.tags.map(t => `#${t}`).join(' ')} />
            )}
            <Meta label="相关度分" value={String(hit?.score ?? '-')} />
          </div>
        )}

        <nav className="drawer-tabs">
          <button className={tab === 'preview' ? 'd-tab active' : 'd-tab'} onClick={() => setTab('preview')}>预览</button>
          <button className={tab === 'related' ? 'd-tab active' : 'd-tab'} onClick={() => setTab('related')}>相关文件</button>
          <button className={tab === 'raw' ? 'd-tab active' : 'd-tab'} onClick={() => setTab('raw')}>原文</button>
        </nav>

        <div className="drawer-body">
          {tab === 'preview' && renderPreview()}
          {tab === 'related' && renderRelated()}
          {tab === 'raw' && renderRaw()}
        </div>
      </div>
    </div>
  )
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="meta-item">
      <div className="meta-label">{label}</div>
      <div className="meta-value">{value}</div>
    </div>
  )
}

function RelatedGroup({ title, items, onClose }: { title: string; items: FileMeta[]; onClose: () => void }) {
  return (
    <section className="related-group">
      <h4>{title}（{items.length}）</h4>
      {items.length === 0 && <div className="empty small">无</div>}
      <ul>
        {items.map(x => (
          <li key={x.file_id}>
            <span className="r-icon">{fileIcon(x.ext, x.mime_type)}</span>
            <div className="r-body">
              <div className="r-name" title={x.path}>{x.name}</div>
              <div className="r-sub">{formatBytes(x.size)} · {formatDate(x.mtime)}</div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

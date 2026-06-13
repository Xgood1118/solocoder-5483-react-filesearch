import { useEffect, useState } from 'react'
import { API } from '@/utils/api'
import type { TopTerm, TopFile, QpsSummary } from '@/types'
import './HotTab.css'

const PALETTE = [
  '#2563eb', '#7c3aed', '#0891b2', '#059669',
  '#d97706', '#dc2626', '#4338ca', '#be185d',
  '#65a30d', '#0d9488', '#4f46e5', '#ea580c',
]

export default function HotTab() {
  const [terms, setTerms] = useState<TopTerm[]>([])
  const [files, setFiles] = useState<TopFile[]>([])
  const [qps, setQps] = useState<QpsSummary | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    setLoading(true)
    try {
      const [t, f, q] = await Promise.all([
        API.topTerms(30),
        API.topFiles(10),
        API.qps(),
      ])
      setTerms(t.data.items)
      setFiles(f.data.items)
      setQps(q.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  const maxCount = terms[0]?.count || 1
  const minCount = terms.length ? terms[terms.length - 1].count : 1
  const sizeOf = (c: number) => {
    if (maxCount === minCount) return 18
    const ratio = (c - minCount) / (maxCount - minCount)
    return 13 + ratio * 22
  }

  const goSearch = (term: string) => {
    window.location.href = `#search?q=${encodeURIComponent(term)}`
    setTimeout(() => window.dispatchEvent(new Event('hashchange')), 0)
  }

  return (
    <div className="hot-tab">
      <div className="hot-head">
        <div>
          <h2>热门搜索与统计</h2>
          <p>展示运营关注的搜索词、Top 被命中文件和 QPS 趋势</p>
        </div>
        <button className="btn" onClick={refresh} disabled={loading}>
          {loading ? '刷新中…' : '刷新数据'}
        </button>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">近 1 小时搜索</div>
          <div className="stat-value">{qps?.total_last_hour ?? 0}</div>
          <div className="stat-sub">次查询</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">近 24 小时搜索</div>
          <div className="stat-value">{qps?.total_last_day ?? 0}</div>
          <div className="stat-sub">次查询</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">峰值 QPM</div>
          <div className="stat-value">{qps?.peak_qpm ?? 0}</div>
          <div className="stat-sub">次 / 分钟</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">活跃搜索词</div>
          <div className="stat-value">{terms.length}</div>
          <div className="stat-sub">个（Top30）</div>
        </div>
      </div>

      <div className="panel">
        <h3>🔥 搜索词云（点击可直接搜索）</h3>
        {terms.length === 0 ? (
          <div className="empty">暂无搜索数据，先去搜索几次吧～</div>
        ) : (
          <div className="wordcloud">
            {terms.map((t, i) => (
              <button
                key={t.term}
                className="cloud-word"
                style={{
                  fontSize: `${sizeOf(t.count)}px`,
                  color: PALETTE[i % PALETTE.length],
                }}
                title={`${t.count} 次`}
                onClick={() => goSearch(t.term)}
              >
                {t.term}
                <span className="cloud-count">{t.count}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="two-col">
        <div className="panel">
          <h3>🏆 搜索词 Top 20</h3>
          {terms.length === 0 ? <div className="empty">暂无</div> : (
            <ol className="rank-list">
              {terms.slice(0, 20).map((t, i) => (
                <li key={t.term} onClick={() => goSearch(t.term)}>
                  <span className={'rank rank-' + Math.min(i + 1, 4)}>{i + 1}</span>
                  <span className="rank-term">{t.term}</span>
                  <span className="rank-count">{t.count}</span>
                </li>
              ))}
            </ol>
          )}
        </div>

        <div className="panel">
          <h3>📊 被命中最多的文件 Top 10</h3>
          {files.length === 0 ? <div className="empty">暂无</div> : (
            <ol className="rank-list">
              {files.map((f, i) => (
                <li key={f.file_id}>
                  <span className={'rank rank-' + Math.min(i + 1, 4)}>{i + 1}</span>
                  <span className="rank-term" title={f.label}>{f.label}</span>
                  <span className="rank-count">{f.count}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>

      <div className="panel">
        <h3>📈 最近 60 分钟搜索量</h3>
        {!qps || qps.per_minute.length === 0 ? <div className="empty">暂无数据</div> : (
          <QpsChart data={qps.per_minute} peak={qps.peak_qpm} />
        )}
      </div>
    </div>
  )
}

function QpsChart({ data, peak }: { data: { bucket: string; count: number }[]; peak: number }) {
  const max = Math.max(peak || 1, 1)
  const w = 800
  const h = 180
  const pad = 36
  const n = data.length
  const step = n > 1 ? (w - pad * 2) / (n - 1) : 0
  const points = data.map((d, i) => {
    const x = pad + i * step
    const y = h - pad - (d.count / max) * (h - pad * 2)
    return { x, y, c: d.count, b: d.bucket }
  })
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
  const areaPath =
    path +
    ` L ${points[points.length - 1].x.toFixed(1)} ${h - pad} L ${points[0].x.toFixed(1)} ${h - pad} Z`

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="qps-chart" preserveAspectRatio="none">
      <defs>
        <linearGradient id="qpsGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2563eb" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#2563eb" stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {[0, 0.25, 0.5, 0.75, 1].map(r => {
        const y = h - pad - r * (h - pad * 2)
        return (
          <g key={r}>
            <line x1={pad} x2={w - pad} y1={y} y2={y} stroke="#eef2f7" />
            <text x={pad - 6} y={y + 3} fontSize="10" fill="#94a3b8" textAnchor="end">
              {Math.round(max * r)}
            </text>
          </g>
        )
      })}
      <path d={areaPath} fill="url(#qpsGrad)" />
      <path d={path} fill="none" stroke="#2563eb" strokeWidth="2" />
      {points.filter((_, i) => i % Math.max(1, Math.floor(n / 6)) === 0).map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="3" fill="white" stroke="#2563eb" strokeWidth="2">
            <title>{p.b}：{p.c}</title>
          </circle>
          <text x={p.x} y={h - 10} fontSize="9" fill="#94a3b8" textAnchor="middle">
            {p.b.slice(11)}
          </text>
        </g>
      ))}
    </svg>
  )
}

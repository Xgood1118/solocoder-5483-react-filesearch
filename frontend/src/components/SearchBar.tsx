import { useState } from 'react'
import './SearchBar.css'

interface Filters {
  path_prefix: string
  mime: string
  from_date: string
  to_date: string
  page_size: number
}

interface Props {
  q: string
  setQ: (v: string) => void
  onSubmit: () => void
  loading: boolean
  filters: Filters
  setFilters: (f: Filters) => void
}

const SUGGESTION_FIELDS = [
  { label: '按文件名', prefix: 'name:' },
  { label: '按路径', prefix: 'path:' },
  { label: '按标签', prefix: 'tag:' },
  { label: '按类型', prefix: 'mime:' },
  { label: '按大小 >10MB', prefix: 'size:>10MB' },
  { label: '按日期', prefix: 'mtime:>2024-01-01' },
]

export default function SearchBar({ q, setQ, onSubmit, loading, filters, setFilters }: Props) {
  const [showHelp, setShowHelp] = useState(false)

  const submit = (e?: React.FormEvent) => {
    e?.preventDefault()
    onSubmit()
  }

  const insertPrefix = (prefix: string) => {
    setQ(prefix + (q ? ' ' + q : ''))
    setShowHelp(false)
  }

  return (
    <form className="searchbar" onSubmit={submit}>
      <div className="searchbar-input-wrap">
        <div className="searchbar-left">
          <span className="search-icon">🔍</span>
          <input
            className="search-input"
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="输入关键词搜索全文，例如：合同 违约金不超过 30%"
            autoFocus
          />
          <button
            type="button"
            className="help-btn"
            title="高级语法"
            onClick={() => setShowHelp(v => !v)}
          >
            ?
          </button>
        </div>
        <button type="submit" className="search-btn" disabled={loading || !q.trim()}>
          {loading ? '搜索中…' : '搜索'}
        </button>

        {showHelp && (
          <div className="help-popover">
            <div className="help-title">快速插入语法</div>
            <div className="help-grid">
              {SUGGESTION_FIELDS.map(s => (
                <button type="button" key={s.prefix} className="help-item" onClick={() => insertPrefix(s.prefix)}>
                  <div className="help-item-prefix">{s.prefix}</div>
                  <div className="help-item-label">{s.label}</div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="filters-row">
        <input
          className="filter-input"
          placeholder="路径前缀，如 /share/contracts"
          value={filters.path_prefix}
          onChange={e => setFilters({ ...filters, path_prefix: e.target.value })}
        />
        <select
          className="filter-input"
          value={filters.mime}
          onChange={e => setFilters({ ...filters, mime: e.target.value })}
        >
          <option value="">全部类型</option>
          <option value="application/pdf">PDF</option>
          <option value="application/vnd.openxmlformats-officedocument">Office</option>
          <option value="text/">文本 / 代码</option>
          <option value="image/">图片</option>
        </select>
        <input
          type="date"
          className="filter-input"
          placeholder="起始日期"
          value={filters.from_date}
          onChange={e => setFilters({ ...filters, from_date: e.target.value })}
        />
        <input
          type="date"
          className="filter-input"
          placeholder="结束日期"
          value={filters.to_date}
          onChange={e => setFilters({ ...filters, to_date: e.target.value })}
        />
        <select
          className="filter-input"
          value={filters.page_size}
          onChange={e => setFilters({ ...filters, page_size: Number(e.target.value) })}
        >
          <option value={10}>每页 10</option>
          <option value={20}>每页 20</option>
          <option value={50}>每页 50</option>
        </select>
      </div>
    </form>
  )
}

import { useEffect, useMemo, useRef, useState } from 'react'
import { API } from '@/utils/api'
import type { SearchHit, SearchResponse } from '@/types'
import { pushHistory, loadHistory, clearHistory, removeHistoryItem } from '@/utils/history'
import SearchBar from '@/components/SearchBar'
import ResultCard from '@/components/ResultCard'
import DetailDrawer from '@/components/DetailDrawer'
import { formatDate } from '@/utils/format'
import './SearchTab.css'

interface Filters {
  path_prefix: string
  mime: string
  from_date: string
  to_date: string
  page_size: number
}

export default function SearchTab() {
  const [q, setQ] = useState('')
  const [filters, setFilters] = useState<Filters>({
    path_prefix: '',
    mime: '',
    from_date: '',
    to_date: '',
    page_size: 20,
  })
  const [loading, setLoading] = useState(false)
  const [resp, setResp] = useState<SearchResponse | null>(null)
  const [error, setError] = useState('')
  const [history, setHistory] = useState(() => loadHistory())
  const [active, setActive] = useState<SearchHit | null>(null)
  const [cursor, setCursor] = useState<string | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const submittedRef = useRef<string>('')
  const filtersRef = useRef<Filters>(filters)
  filtersRef.current = filters

  const runSearch = async (nextCursor?: string | null) => {
    const query = q.trim()
    if (!query) return
    submittedRef.current = query
    const f = filtersRef.current
    setLoading(!nextCursor)
    if (nextCursor) setLoadingMore(true)
    setError('')
    try {
      const { data } = await API.search({
        q: query,
        path_prefix: f.path_prefix || undefined,
        mime: f.mime || undefined,
        from_date: f.from_date || undefined,
        to_date: f.to_date || undefined,
        page_size: f.page_size,
        cursor: nextCursor || undefined,
      })
      if (!nextCursor) {
        setResp(data)
        pushHistory(query)
        setHistory(loadHistory())
      } else {
        setResp(prev => prev ? {
          ...data,
          results: [...prev.results, ...data.results],
        } : data)
      }
      setCursor(data.cursor)
    } catch (e: any) {
      setError(e?.message || '搜索请求失败')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  const onSubmit = () => {
    setCursor(null)
    runSearch(null)
  }

  const onLoadMore = () => {
    if (!cursor || loadingMore) return
    runSearch(cursor)
  }

  const applyHistory = (item: { q: string }) => {
    setQ(item.q)
    setTimeout(() => {
      setCursor(null)
      runSearch(null)
    }, 0)
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const initQ = params.get('q')
    if (initQ) {
      setQ(initQ)
      setTimeout(() => runSearch(null), 0)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const summary = useMemo(() => {
    if (!resp) return null
    const r = resp.results
    return {
      count: r.length,
      top_mime: topN(r.map(x => x.ext), 5),
      avg_score: r.length ? (r.reduce((s, x) => s + x.score, 0) / r.length).toFixed(3) : '0',
    }
  }, [resp])

  return (
    <div className="search-tab">
      <SearchBar
        q={q}
        setQ={setQ}
        onSubmit={onSubmit}
        loading={loading}
        filters={filters}
        setFilters={setFilters}
      />

      <div className="search-layout">
        <aside className="search-sidebar">
          <div className="sidebar-block">
            <div className="sidebar-head">
              <span>搜索历史</span>
              {history.length > 0 && (
                <button className="linkbtn" onClick={() => { clearHistory(); setHistory([]) }}>清空</button>
              )}
            </div>
            <div className="history-list">
              {history.length === 0 && <div className="empty">暂无历史（localStorage 本地保存）</div>}
              {history.map((h, i) => (
                <div key={i} className="history-row" title={`${formatDate(h.at / 1000)}`}>
                  <span className="history-q" onClick={() => applyHistory(h)}>{h.q}</span>
                  <button className="xbtn" title="删除" onClick={() => { removeHistoryItem(h.q); setHistory(loadHistory()) }}>×</button>
                </div>
              ))}
            </div>
          </div>
          <div className="sidebar-block">
            <div className="sidebar-head"><span>语法提示</span></div>
            <div className="syntax">
              <div><code>关键词1 关键词2</code> AND 组合</div>
              <div><code>"不可抗力"</code> 短语匹配</div>
              <div><code>A OR B</code> OR 组合</div>
              <div><code>-违规</code> 排除词</div>
              <div><code>name:合同</code> 字段限定</div>
              <div><code>tag:法律</code> 按标签</div>
              <div><code>mime:pdf</code> 按类型</div>
              <div><code>size:{'>'}10MB</code> 按大小</div>
              <div><code>mtime:{'>'}2024-01-01</code> 按时间</div>
            </div>
          </div>
        </aside>

        <section className="search-results">
          {error && <div className="errbox">{error}</div>}
          {loading && <div className="loading">正在搜索…</div>}
          {!loading && resp && summary && (
            <div className="results-summary">
              已返回 <b>{summary.count}</b> 条，
              平均相关度 <b>{summary.avg_score}</b>
              {resp.parsed?.error && <span className="parse-warn"> · 解析提示：{resp.parsed.error}</span>}
              {resp.parsed?.and_terms?.length > 0 && (
                <span className="chips">
                  {resp.parsed.and_terms.map((t, i) => <span key={i} className="chip">AND {t}</span>)}
                  {resp.parsed.or_terms.map((t, i) => <span key={'o' + i} className="chip or">OR {t}</span>)}
                  {resp.parsed.not_terms.map((t, i) => <span key={'n' + i} className="chip not">NOT {t}</span>)}
                  {resp.parsed.phrases.map((t, i) => <span key={'p' + i} className="chip phrase">"{t}"</span>)}
                  {resp.parsed.field_filters.map(([f, op, v], i) => (
                    <span key={'f' + i} className="chip field">{f}{op}{v}</span>
                  ))}
                </span>
              )}
            </div>
          )}
          {!loading && resp?.results?.length === 0 && <div className="empty">未找到结果，换个关键词试试？</div>}
          {resp?.results?.map((hit) => (
            <ResultCard key={hit.file_id} hit={hit} onClick={() => setActive(hit)} />
          ))}
          {!loading && cursor && (
            <div className="loadmore-wrap">
              <button className="btn primary" disabled={loadingMore} onClick={onLoadMore}>
                {loadingMore ? '加载中…' : '加载更多'}
              </button>
              <div className="cursor-note">使用 cursor 分页，不返回总条数</div>
            </div>
          )}
        </section>
      </div>

      <DetailDrawer hit={active} onClose={() => setActive(null)} />
    </div>
  )
}

function topN(arr: string[], n: number) {
  const map = new Map<string, number>()
  arr.forEach(x => map.set(x, (map.get(x) || 0) + 1))
  return Array.from(map.entries()).sort((a, b) => b[1] - a[1]).slice(0, n)
}

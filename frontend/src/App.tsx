import { useEffect, useState } from 'react'
import SearchTab from '@/pages/SearchTab'
import HotTab from '@/pages/HotTab'
import IndexStatusTab from '@/pages/IndexStatusTab'
import './App.css'

type TabId = 'search' | 'hot' | 'status'

export default function App() {
  const [tab, setTab] = useState<TabId>(() => {
    const hash = window.location.hash.replace('#', '') as TabId
    return (['search', 'hot', 'status'].includes(hash) ? hash : 'search') as TabId
  })

  useEffect(() => {
    const onHash = () => {
      const h = window.location.hash.replace('#', '') as TabId
      if (['search', 'hot', 'status'].includes(h)) setTab(h)
    }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const go = (id: TabId) => {
    setTab(id)
    window.location.hash = id
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-title">
          <span className="logo">🔎</span>
          <div>
            <h1>NAS 全文检索</h1>
            <p>基于 Whoosh + jieba 的中文全文检索 · BM25 + 字段权重</p>
          </div>
        </div>
        <nav className="tabs">
          <button className={tab === 'search' ? 'tab active' : 'tab'} onClick={() => go('search')}>
            搜索
          </button>
          <button className={tab === 'hot' ? 'tab active' : 'tab'} onClick={() => go('hot')}>
            热门搜索
          </button>
          <button className={tab === 'status' ? 'tab active' : 'tab'} onClick={() => go('status')}>
            索引状态
          </button>
        </nav>
      </header>
      <main className="app-main">
        {tab === 'search' && <SearchTab />}
        {tab === 'hot' && <HotTab />}
        {tab === 'status' && <IndexStatusTab />}
      </main>
    </div>
  )
}

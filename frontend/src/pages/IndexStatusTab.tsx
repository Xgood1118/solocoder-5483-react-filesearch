import { useEffect, useState } from 'react'
import { API } from '@/utils/api'
import type { IndexStatus } from '@/types'
import { formatDate, formatBytes } from '@/utils/format'
import './IndexStatusTab.css'

export default function IndexStatusTab() {
  const [st, setSt] = useState<IndexStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [rebuilding, setRebuilding] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await API.indexStatus()
      setSt(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 10_000)
    return () => clearInterval(t)
  }, [])

  const trigger = async () => {
    if (rebuilding || st?.in_progress) return
    setRebuilding(true)
    setMsg(null)
    try {
      const { data } = await API.indexRebuild()
      setMsg({ ok: data.ok, text: data.ok ? '已启动增量更新，后台正在构建…' : data.msg })
      setTimeout(load, 2000)
    } catch (e: any) {
      setMsg({ ok: false, text: e?.response?.status === 409 ? '已在构建中' : '启动失败' })
    } finally {
      setRebuilding(false)
    }
  }

  return (
    <div className="status-tab">
      <div className="status-head">
        <div>
          <h2>索引状态</h2>
          <p>Whoosh 索引、扫描进度、抽取失败记录，每 10s 自动刷新</p>
        </div>
        <div className="status-actions">
          <button className="btn" onClick={load} disabled={loading}>刷新</button>
          <button
            className="btn primary"
            onClick={trigger}
            disabled={rebuilding || st?.in_progress || loading}
          >
            {st?.in_progress ? '构建中…' : '触发增量更新'}
          </button>
        </div>
      </div>

      {msg && (
        <div className={'msg ' + (msg.ok ? 'ok' : 'warn')}>{msg.text}</div>
      )}

      {loading && <div className="empty">加载中…</div>}

      {!loading && st && (
        <>
          <div className="status-grid">
            <StatusCard
              label="已扫描文件总数"
              value={st.total_files_scanned}
              sub="遍历配置根目录下的文件"
              icon="📁"
            />
            <StatusCard
              label="已建立索引"
              value={st.indexed_count}
              sub="可被搜索到的文档数"
              icon="✅"
              accent
            />
            <StatusCard
              label="抽取失败"
              value={st.failed_count}
              sub="OCR 失败、文件损坏、加密等"
              icon="⚠️"
              warn={st.failed_count > 0}
            />
            <StatusCard
              label="已删除文档"
              value={st.deleted_count}
              sub="路径消失后清理的索引"
              icon="🗑️"
            />
            <StatusCard
              label="跳过未变更"
              value={st.skipped_count}
              sub="mtime 未变化无需重抽"
              icon="⏭️"
            />
            <StatusCard
              label="最近一次更新"
              value={st.last_update || '从未'}
              sub={st.last_update_ts ? formatDate(st.last_update_ts) : ''}
              icon="🕒"
              stringVal
            />
          </div>

          {st.in_progress && (
            <div className="progress-banner">🔄 后台正在构建索引，请勿重复触发</div>
          )}

          <div className="panel">
            <h3>🔧 部署信息</h3>
            <div className="kv-list">
              <KV label="索引目录" value={st.index_dir} mono />
              <KV label="扫描根目录" value={st.root_dir} mono />
              <KV label="状态" value={st.in_progress ? '构建中' : '空闲'} />
              <KV label="索引引擎" value="Whoosh 2.7 (BM25F + jieba 中文分词)" />
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <h3>🧾 最近抽取失败（最多 20 条，完整记录在 data/logs/errors.log）</h3>
              <span className="badge">{st.recent_failures.length}</span>
            </div>
            {st.recent_failures.length === 0 ? (
              <div className="empty">🎉 暂无失败记录</div>
            ) : (
              <div className="failure-list">
                {st.recent_failures.map((f, i) => (
                  <div key={i} className="failure-row">
                    <div className="failure-ts">{formatDate(f.ts)}</div>
                    <div className="failure-path" title={f.path}>{f.path}</div>
                    <div className="failure-err">{f.error}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="panel">
            <h3>💡 关于索引与部署边界</h3>
            <ul className="tips">
              <li>Whoosh 索引存储在本地磁盘，单机部署时直接挂载共享卷即可工作。</li>
              <li>多副本部署需要保证每台机器索引一致，建议后续切换到主从同步或 Elasticsearch。</li>
              <li>首次 10 万份文件构建约 4 小时，增量更新按 mtime 对比，单文件秒级。</li>
              <li>OCR 识别为异步队列，扫描页会先占位再回填索引文字，期间需等待任务完成。</li>
              <li>搜索历史保存在浏览器 localStorage，跨浏览器/清缓存会丢失，如需持久化请接入后端。</li>
            </ul>
          </div>
        </>
      )}
    </div>
  )
}

function StatusCard({
  label, value, sub, icon, accent, warn, stringVal,
}: {
  label: string; value: number | string; sub?: string; icon?: string;
  accent?: boolean; warn?: boolean; stringVal?: boolean;
}) {
  return (
    <div className={'stat-card' + (accent ? ' accent' : '') + (warn ? ' warn' : '')}>
      {icon && <div className="sc-icon">{icon}</div>}
      <div className="sc-label">{label}</div>
      <div className="sc-value">
        {stringVal ? value : typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      {sub && <div className="sc-sub">{sub}</div>}
    </div>
  )
}

function KV({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="kv">
      <div className="kv-label">{label}</div>
      <div className={'kv-value' + (mono ? ' mono' : '')}>{value}</div>
    </div>
  )
}

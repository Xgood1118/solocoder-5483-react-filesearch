import React, { useState, useEffect } from 'react';
import axios from 'axios';

// 前端搜索组件示例代码
// 演示文件名搜索时如何带高亮渲染
interface SearchResult {
  id: string;
  name: string;
  path: string;
  snippet: string;
  score: number;
}

const HighlightedSnippet: React.FC<{
  html: string;
  keywords: string[];
}> = ({ html }) => {
  // 注意：这里用 dangerouslySetInnerHTML 渲染后端处理过的高亮 HTML
  // XSS 防护：后端已经把关键词、内容 escape 后再包 <mark>
  // 前端做二次校验，移除所有 onxxx= 属性注入
  const sanitized = html
    .replace(/\son\w+\s*=/gi, ' data-removed=')
    .replace(/javascript\s*:/gi, 'data-invalid:');
  return <div className="snippet" dangerouslySetInnerHTML={{ __html: sanitized }} />;
};

export default function SearchDemo() {
  const [q, setQ] = useState('合同');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const run = async () => {
      if (!q) return;
      setLoading(true);
      try {
        // 违约金不超过 30% —— 测试关键词
        const { data } = await axios.get('/api/search', { params: { q } });
        setResults(data.results);
      } finally {
        setLoading(false);
      }
    };
    const t = setTimeout(run, 300);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <div>
      <input value={q} onChange={e => setQ(e.target.value)} />
      {loading && <p>加载中…</p>}
      {results.map(r => (
        <article key={r.id}>
          <h3>{r.name}</h3>
          <HighlightedSnippet html={r.snippet} keywords={[q]} />
          <div>相关度: {r.score.toFixed(3)}</div>
        </article>
      ))}
    </div>
  );
}

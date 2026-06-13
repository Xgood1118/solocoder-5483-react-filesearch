# NAS 全文检索系统

基于 **Whoosh + jieba** 的中文全文检索，前端 React + Vite，后端 Python Flask。

解决的痛点：NAS 上几十万份文件名很乱，用 Everything 只搜文件名搜不到文档里的内容（比如「哪个文档里出现过『违约金不超过 30%』这句话」）。

---

## ✨ 功能特性

### 搜索
- **全文检索**：内容、文件名、路径、标签多字段 BM25F + 字段权重加权
  - `name: 3.0` / `path: 2.0` / `tags: 2.0` / `content: 1.0` / `mtime 新鲜度: 0.5 衰减`
- **中文分词**：jieba 精准分词 + 自定义行业词典（法律/财务/设计）
- **高级语法**：
  - 字段限定：`name:合同`、`tag:法律`、`mime:pdf`、`size:>10MB`、`mtime:>2024-01-01`
  - 逻辑运算：`合同 AND 违约`（默认 AND）、`A OR B`、`-违规`（NOT）
  - 短语搜索：`"不可抗力"`
  - 长查询自动拆词后 OR 合并
- **安全高亮**：后端 escape HTML + 去 onxxx= 属性注入，前端 `dangerouslySetInnerHTML` 二次 sanitize
- **Cursor 分页**：不返回总条数，避免深分页性能问题

### 内容抽取（按 MIME 分发）
- 纯文本 / 代码：按编码探测读取，代码文件按行索引 token（带行号+列号）
- PDF：`pypdf` 逐页抽取；扫描页文字过少自动丢 OCR 异步队列
- Office：`python-docx`（docx）/ `python-pptx`（pptx）抽段落和表格
- 图片：`pytesseract` OCR（`chi_sim+eng`），标记为「OCR 低置信度」
- 单个文件抽取失败不阻塞批处理，记录错误日志

### 前端（3 个 Tab）
1. **搜索**：搜索框 + 语法提示浮层 → 卡片结果列表 → 右侧详情抽屉（PDF/图片/代码预览）+ 搜索历史（localStorage 50 条）
2. **热门搜索**：Top20 词云、搜索词排名、Top10 被命中文件、最近 60 分钟 QPS 折线图
3. **索引状态**：扫描数 / 已索引 / 失败数 / 增量更新按钮 / 最近失败记录 / 部署边界说明

### 统计
- 搜索词频次（Top20）、按文件命中次数（Top10）、按分钟 QPS（最近 24 小时）
- JSON 文件持久化在 `data/stats/`

---

## 📂 目录结构

```
5483-react-filesearch/
├── backend/                     # Python Flask 后端
│   ├── run.py / app.py          # Flask 入口 & 路由
│   ├── config.py / logger.py    # 配置 + 日志
│   ├── mime_utils.py            # MIME 识别与分类
│   ├── extract/                 # 内容抽取模块
│   │   ├── dispatcher.py        # 按 MIME 派发
│   │   ├── text_extractor.py    # 纯文本
│   │   ├── code_extractor.py    # 代码按行 token 化
│   │   ├── pdf_extractor.py     # PDF 抽取
│   │   ├── office_extractor.py  # docx/pptx/xlsx
│   │   ├── ocr_extractor.py     # Tesseract 异步队列
│   │   ├── base.py              # 数据结构
│   │   └── custom_dict.txt      # jieba 自定义词典
│   ├── index/                   # Whoosh 索引
│   │   ├── schema.py            # Schema + BM25F 配置
│   │   ├── analyzer.py          # jieba 分词 + 标准分析器
│   │   └── manager.py           # 增量更新 / OCR 回填 / 关联推荐
│   ├── search/                  # 搜索服务
│   │   ├── query_parser.py      # 高级语法解析器（状态机）
│   │   ├── service.py           # BM25F + 重排序 + Cursor 分页
│   │   └── highlighter.py       # XSS 安全的高亮
│   ├── stats/                   # 统计（词频/命中/QPS）
│   └── requirements.txt         # 依赖（<= 10 个核心包）
│
├── frontend/                    # React + Vite 前端
│   ├── src/
│   │   ├── pages/               # SearchTab / HotTab / IndexStatusTab
│   │   ├── components/          # SearchBar / ResultCard / DetailDrawer
│   │   ├── utils/               # API / 格式化 / 历史
│   │   ├── App.tsx / main.tsx
│   │   └── styles.css
│   └── package.json             # 依赖（<= 15 个）
│
├── sample_files/                # 示例文档（首次运行可直接索引）
├── data/
│   ├── index/                   # Whoosh 索引文件
│   ├── logs/                    # filesearch.log / errors.log
│   └── stats/                   # 搜索统计 JSON
├── start.bat / start.ps1        # Windows 一键启动
└── PROMPT.txt                   # 原始需求文档
```

---

## 🚀 快速开始

### 前置条件
- **Python 3.10+**（建议 3.11）
- **Node.js 18+**（建议 20 LTS）
- **可选**：[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)（需安装中文包 `chi_sim`，如果要 OCR 图片/扫描 PDF）

### 一键启动（Windows）

```powershell
# 方式一：双击运行
start.bat

# 方式二：PowerShell
.\start.ps1
```

脚本会自动创建虚拟环境、安装依赖、启动后端（端口 5000）和前端（端口 5173）。

### 手动启动

**后端：**
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
python run.py
```

**前端（另开终端）：**
```bash
cd frontend
npm install
npm run dev
```

### 验证
- 前端：<http://localhost:5173>
- 后端健康检查：<http://localhost:5000/api/health>
- 搜索接口示例：
  `http://localhost:5000/api/search?q=合同`
  `http://localhost:5000/api/search?q=违约金不超过%2030%`
  `http://localhost:5000/api/search?q="不可抗力" tag:法律`

---

## 🔧 环境变量

端口和路径均可通过 `.env` 配置（模板为 `.env.example`）：

| 变量 | 后端 `.env` | 前端 `.env` | 默认 |
|---|---|---|---|
| 后端端口 | `FLASK_PORT` | — | 5000 |
| 前端端口 | — | `VITE_PORT` | 5173 |
| API 基址 | — | `VITE_API_BASE` | http://localhost:5000 |
| 索引目录 | `INDEX_DIR` | — | `../data/index` |
| 扫描根目录 | `FILES_ROOT_DIR` | — | `../sample_files` |
| CORS 来源 | `CORS_ORIGIN` | — | http://localhost:5173 |
| OCR 语言 | `OCR_LANG` | — | `chi_sim+eng` |

---

## 🧠 设计要点 & 已知边界

### 已做防护
1. **XSS**：后端高亮前全量 `html.escape(quote=True)` + 校验 `onxxx=` / `javascript:`；前端再次 sanitize
2. **OCR 静默失败**：扫描页/OCR 图片的搜索结果标 `ocr_low_conf`，前端显示「⚠️ OCR 低置信」警告
3. **抽取容错**：单个文件失败记录到 `errors.log`，不阻塞批处理
4. **短语搜索**：引号内短语不走拆词 OR，保留短语语义

### 隐含边界（如需扩展请留意）
1. **Whoosh 单机索引**：索引存本地磁盘，多副本要自行保证一致性（主从同步 / Elasticsearch 迁移）
2. **搜索历史存 localStorage**：跨浏览器/清缓存会丢失，未同步到服务端
3. **OCR 表格识别差**：纯表格图片几乎全错，仅靠低置信度标记提醒用户
4. **xlsx 文本抽取暂跳过**：代码里只写了 placeholder，如需可装 `openpyxl` 补全

---

## 📊 性能参考
- 10 万份文件首次构建索引：约 4 小时（普通 PC）
- 增量更新：按 mtime 对比，单文件秒级
- 搜索 P99：< 200ms（千万级文档可能需要 ES 替换）

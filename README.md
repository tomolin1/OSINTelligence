# 开源威胁情报APT研判系统

网络空间安全综合实验 — 实验三：基于大模型的威胁情报研判系统

## 各小组快速上手指南

### 📌 数据与样本组（爬虫组）

**需要先看的文件：**
1. 读 `数据格式契约.docx` 第一章 → 搞清楚爬虫输出要什么字段
2. 读 `schema.json` → `crawler.output_format` 字段定义
3. 看 `sample_crawler_output.json` → 照着这个格式输出

**你的任务：**

**1. 写爬虫（泛采）**
- 目标来源：威胁情报报告、安全新闻、CVE 数据库、安全博客
- 输出每个来源为一个 `.json` 文件，格式必须匹配 `schema.json` 的 `crawler.output_format`
- 所有文件保存到 `data/crawler_output/` 目录
- 关键：`raw_text` 必须为纯文本（去掉 HTML/JS/CSS）

**2. 做黄金测试集（精标）**
- 手写 `data/golden.json`，按 `golden_format_spec.md` 格式
- 从维基/报告/ATT&CK 中摘取 APT28、Lazarus、Kimsuky 的真实实体和关系

**参考来源：**
- https://attack.mitre.org/groups/G0007/ (APT28)
- https://attack.mitre.org/groups/G0032/ (Lazarus)
- https://attack.mitre.org/groups/G0094/ (Kimsuky)

**你的输出：**
```
data/crawler_output/          ← 爬虫产出的 JSON
data/golden.json              ← 黄金测试集
```

---

### 📌 LLM 抽取与分析组

**需要先看的文件：**
1. 读 `数据格式契约.docx` 第二章 → 搞清楚 LLM 要输出什么
2. 读 `schema.json` → `llm_extraction.output_format` 格式定义
3. 看 `sample_llm_output.json` → 照着这个格式输出
4. 读 `backend/services/llm_service.py` → 后端已经集成了 LLM 调用框架，直接在此基础上改

**你的任务：**

**1. 调 Prompt（最重要）**
- 修改 `backend/services/llm_service.py` 中的 `SYSTEM_PROMPT`
- 先用黄金测试集调稳，再上全量数据
- 必须确保 LLM 输出 100% 合法 JSON（已有 try...except 重试机制）

**2. 跑通管道**
```
爬虫 JSON → 读 raw_text → 调 LLM API → 解析 JSON → 存 Neo4j
```
后端代码已经搭好了框架，你只需要优化 Prompt 即可。

**3. 断点续传**
- 已处理的文件写 `.done` 标记，防止重复烧钱
- 后端已经在 `batch_analyze` 接口中实现了

**注意事项：**
- ❌ 绝对不要自己去写爬虫
- ❌ 绝对不要自己画前端
- ✅ 先用黄金测试集调 Prompt
- ✅ 注意 Token 消耗，单次调用很贵

---

### 📌 图谱与前端组

**技术栈：** React + ECharts-for-React + FastAPI

**需要先看的文件：**
1. 读 `api_docs.md` → 搞清楚有哪些 API 和响应格式
2. 读 `数据格式契约.docx` 第三章 → 搞清楚 Neo4j 节点和关系结构
3. 下载 `mock_data.json` → 后端 API 完成前用来开发

**你的任务（分步进行）：**

**第一步：搭建 React 项目**
```bash
npx create-react-app frontend
cd frontend
npm install echarts echarts-for-react
```
- 组件结构：`App.js` → `GraphChart.js`（图谱）+ `SearchPanel.js`（搜索）+ `DetailPanel.js`（详情）
- 暗色风格，参考 `mockup_react.html` 的布局

**第二步：用 Mock 数据先画页面（不用等后端）**
```javascript
// 直接从 mock_data.json 加载
import mockData from './mock_data.json';

// 用 ECharts 力导向图渲染
<ReactECharts option={graphOption} />
```
- ECharts 配置：`series.type: 'graph'` + `layout: 'force'`
- 节点按 `group` 字段着色（见 `api_docs.md` 第 3.1 节颜色表）

**第三步：实现三个核心交互**
- ① 鼠标悬停 → 显示详情
- ② 点击节点 → 展开关联（爆炸图）→ 调用 `GET /api/v1/graph/expand/:id`
- ③ 时间轴滑动 → 过滤时间范围 → 调用 `GET /api/v1/graph/timeline`

**第四步：接真实数据**
```javascript
// 把 mock 数据替换成 FastAPI 后端
const data = await fetch('/api/v1/graph?entity_id=ENT_APT_GROUP_apt28_001')
  .then(res => res.json());
```

**对接后端 API（FastAPI）：**
- 搜索框 → `GET /api/v1/entities/search?q=APT28`
- 图谱渲染 → `GET /api/v1/graph?entity_id=xxx`
- 展开节点 → `GET /api/v1/graph/expand/:id`
- 时间轴 → `GET /api/v1/graph/timeline?start=2025-01-01&end=2025-12-31`
- 实体详情 → `GET /api/v1/entities/:id`
- 生成报告 → `GET /api/v1/report?entity_id=xxx`

**渲染优化：**
- 默认只渲染 2 层关系
- 深层关系用「点击加载更多」
- 节点超过 200 个启用 ECharts 的 `roam: true` 缩放

---

### 📌 报告答辩与测试组

**需要先看的文件：**
1. 读 `api_docs.md` → 搞清楚 API 接口
2. 读 `golden_format_spec.md` → 测试标准
3. 读 `mock_data.json` → 了解数据的形状

**你的任务（贯穿全周期）：**

**1. 测试（质量门禁）**
- 拿数据组的 `golden.json`，每天调 LLM 组的 API 灌数据
- 比对抽取结果 vs 黄金集
- 准确率 / 召回率 / F1 不达标 → 打回 LLM 组调 Prompt
- 把每次迭代结果记录到报告里

**2. 写实验报告**
- 按「采集→清洗→抽取→建图→展示」流水线写
- 人员分工及工作量占比写圆润

**3. 做 PPT 和演示视频**
- 提前录好操作录像（防现场断网）

---

## 数据流总览

```
爬虫组                            LLM组                             前端组
  │                                │                                │
  ├─ 威胁报告.json ──┐             │                                │
  ├─ CVE数据.json    ├───→ LLM抽取 ──→ Neo4j ──→ REST API ──→ 图谱渲染
  ├─ 新闻.json      │   (实体+关系)  │       (FastAPI)    │  (ECharts)
  └─ 论坛.json ────┘              │                     │
                                   │                     └── mock_data.json(先)
                                   │                        (开发阶段替代API)
                                  测试组 ←── golden.json ──┘
                                       ↑── 每天验证抽取质量
```

## 仓库结构

```
├── README.md                 ← 本文件（各组从这里开始）
├── schema.json               ← 数据格式契约（全组都必须遵守）
├── api_docs.md               ← API 接口文档
├── mock_data.json            ← 前端的 Mock 数据
├── 数据格式契约.docx          ← 爬虫/LLM/Neo4j 格式说明
├── 架构设计文档.docx           ← 系统架构设计
├── golden_format_spec.md     ← 黄金测试集格式规范
├── sample_crawler_output.json← 爬虫输出示例
├── sample_llm_output.json    ← LLM 输出示例
│
├── backend/                  ← 后端代码（FastAPI）
│   ├── main.py               ← 启动入口
│   ├── config.py             ← 系统配置
│   ├── requirements.txt      ← Python 依赖
│   ├── models/               ← 数据模型
│   ├── routers/              ← API 路由
│   └── services/             ← 服务层（LLM + Neo4j）
│
├── data/                     ← 数据目录（各组自行创建）
│   ├── crawler_output/       ← 爬虫输出（数据组）
│   ├── golden.json           ← 黄金测试集（数据组）
│   └── processed/            ← 已处理标记（LLM组）
│
└── frontend/                 ← React 前端页面（前端组自行创建）
    ├── src/
    │   ├── App.js            ← 主页面
    │   ├── GraphChart.js     ← ECharts 图谱组件
    │   ├── SearchPanel.js    ← 搜索组件
    │   └── DetailPanel.js    ← 详情面板组件
    └── package.json
```

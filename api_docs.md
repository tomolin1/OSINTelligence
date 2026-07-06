# 开源威胁情报APT研判系统 — API接口文档

> **版本**: v1.0 | **最后更新**: 2026-07-06  
> **维护者**: 架构与数据规范组  
> **基础URL**: `/api/v1`  
> **数据格式**: 所有请求和响应均为 `application/json`（除 `/analyze/file` 为 `multipart/form-data`）

---

## 目录

1. [约定与规范](#1-约定与规范)
2. [分析接口](#2-分析接口)
3. [图谱接口](#3-图谱接口)
4. [实体接口](#4-实体接口)
5. [报告接口](#5-报告接口)
6. [系统接口](#6-系统接口)
7. [附录：前端集成指南](#7-附录前端集成指南)

---

## 1. 约定与规范

### 1.1 通用响应格式

**成功响应**:
```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2026-07-06T12:00:00Z"
}
```

**错误响应**:
```json
{
  "success": false,
  "error": {
    "code": "ERR_VALIDATION_001",
    "message": "请求参数校验失败",
    "details": { "field": "text", "reason": "text不能为空" }
  },
  "timestamp": "2026-07-06T12:00:00Z"
}
```

### 1.2 错误码表

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| `ERR_VALIDATION_001` | 400 | 请求参数校验失败 |
| `ERR_LLM_001` | 500 | LLM API调用失败 |
| `ERR_LLM_002` | 500 | LLM返回格式非法（非JSON） |
| `ERR_LLM_003` | 429 | LLM API速率限制 |
| `ERR_DB_001` | 500 | Neo4j数据库操作失败 |
| `ERR_DB_002` | 404 | 实体未找到 |
| `ERR_FILE_001` | 400 | 文件格式不支持 |
| `ERR_FILE_002` | 400 | 文件大小超限（限制：10MB） |
| `ERR_CRAWLER_001` | 500 | 爬虫执行失败 |
| `ERR_AUTH_001` | 401 | API密钥验证失败 |

### 1.3 数据类型映射

| Schema类型 | JSON类型 | Neo4j类型 | 说明 |
|-----------|---------|-----------|------|
| `APT_GROUP` | object | `:APT_GROUP` | APT组织节点 |
| `MALWARE` | object | `:MALWARE` | 恶意软件节点 |
| `TOOL` | object | `:TOOL` | 攻击工具节点 |
| `CVE` | object | `:CVE` | 漏洞节点 |
| `TECHNIQUE` | object | `:TECHNIQUE` | MITRE ATT&CK技术节点 |
| `PERSON` | object | `:PERSON` | 人员节点 |
| `COUNTRY` | object | `:COUNTRY` | 国家节点 |
| `INDUSTRY` | object | `:INDUSTRY` | 行业节点 |
| `CAMPAIGN` | object | `:CAMPAIGN` | 攻击活动节点 |
| `ORGANIZATION` | object | `:ORGANIZATION` | 通用组织节点 |
| `TIME` | object | `:TIME` | 时间实体节点 |

---

## 2. 分析接口

### 2.1 单文本分析

提交文本进行LLM实体关系抽取。

```
POST /api/v1/analyze
```

**Request Body**:
```json
{
  "text": "APT28，也被称为Fancy Bear，被确认与俄罗斯GRU有关联。该组织在2025年利用LameHug恶意软件对乌克兰目标发动了网络攻击，利用了CVE-2025-12345漏洞。",
  "source_url": "https://example.com/threat-report/apt28-2025",
  "language": "zh",
  "source_type": "threat_report"
}
```

**Response `200`**:
```json
{
  "success": true,
  "data": {
    "document_id": "a1b2c3d4e5f67890",
    "entities": [
      {
        "id": "ENT_APT_GROUP_a1b2c3d4",
        "name": "APT28",
        "type": "APT_GROUP",
        "aliases": ["Fancy Bear", "Sofacy", "Sednit"],
        "description": "与俄罗斯GRU有关联的APT组织",
        "source_text": "APT28，也被称为Fancy Bear，被确认与俄罗斯GRU有关联",
        "confidence": 0.95
      },
      {
        "id": "ENT_MALWARE_e5f6a7b8",
        "name": "LameHug",
        "type": "MALWARE",
        "description": "APT28使用的恶意软件",
        "source_text": "该组织在2025年利用LameHug恶意软件",
        "confidence": 0.88
      },
      {
        "id": "ENT_CVE_c9d0e1f2",
        "name": "CVE-2025-12345",
        "type": "CVE",
        "description": "APT28利用的漏洞",
        "source_text": "利用了CVE-2025-12345漏洞",
        "confidence": 0.92
      }
    ],
    "relationships": [
      {
        "id": "REL_001",
        "source_id": "ENT_APT_GROUP_a1b2c3d4",
        "target_id": "ENT_MALWARE_e5f6a7b8",
        "type": "USES",
        "description": "APT28使用LameHug恶意软件",
        "source_text": "APT28利用LameHug恶意软件对乌克兰目标发动了网络攻击",
        "confidence": 0.85
      },
      {
        "id": "REL_002",
        "source_id": "ENT_APT_GROUP_a1b2c3d4",
        "target_id": "ENT_CVE_c9d0e1f2",
        "type": "EXPLOITS",
        "description": "APT28利用CVE-2025-12345漏洞",
        "source_text": "利用了CVE-2025-12345漏洞",
        "confidence": 0.80
      }
    ],
    "summary": {
      "overview": "APT28（Fancy Bear）利用LameHug恶意软件和CVE-2025-12345漏洞攻击乌克兰目标",
      "key_findings": [
        "APT28与俄罗斯GRU有关联",
        "APT28在2025年仍保持活跃",
        "LameHug恶意软件被用于针对乌克兰的攻击"
      ],
      "threat_level": "HIGH",
      "relevant_ttps": ["T1566", "T1203", "T1059"]
    },
    "analysis_time": "2026-07-06T12:00:00Z"
  }
}
```

**Response `400`**:
```json
{
  "success": false,
  "error": {
    "code": "ERR_VALIDATION_001",
    "message": "text字段为必填项，且长度需在10-50000字符之间",
    "details": { "field": "text", "reason": "text不能为空" }
  },
  "timestamp": "2026-07-06T12:00:00Z"
}
```

### 2.2 文件分析

上传爬虫输出文件进行批量实体关系抽取。

```
POST /api/v1/analyze/file
```

**Request**: `multipart/form-data`
- `file`: 支持 `.json`（爬虫输出格式）或 `.txt`（纯文本）

**Response**: 同 [2.1 单文本分析](#21-单文本分析) 的 `200` 响应

### 2.3 批量分析

批量分析指定目录下所有未处理过的爬虫输出文件。

```
POST /api/v1/analyze/batch
```

**Request Body**:
```json
{
  "directory": "/data/crawler_output/",
  "resume": true
}
```

**Response `200`**:
```json
{
  "success": true,
  "data": {
    "total_files": 50,
    "processed": 45,
    "failed": 2,
    "skipped": 3,
    "errors": [
      { "file": "report_03.json", "error": "LLM API超时" },
      { "file": "report_27.json", "error": "文本长度超过限制" }
    ],
    "results": [ ... ]
  }
}
```

### 2.4 分析状态查询

查询某文档的分析状态。

```
GET /api/v1/analyze/status/:document_id
```

**Response `200`**:
```json
{
  "success": true,
  "data": {
    "document_id": "a1b2c3d4e5f67890",
    "status": "completed",
    "progress": 1.0,
    "entity_count": 12,
    "relationship_count": 8,
    "analysis_time_seconds": 3.5
  }
}
```

---

## 3. 图谱接口

### 3.1 获取图数据

获取知识图谱数据，用于前端D3.js/ECharts渲染。

```
GET /api/v1/graph
```

**Query Parameters**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `entity_id` | string | 否 | - | 中心实体ID，不传返回全图概览 |
| `depth` | int | 否 | `2` | 关系展开深度（最大2层） |
| `types` | string | 否 | - | 按实体类型过滤，逗号分隔 |
| `time_range` | string | 否 | - | 时间范围: `start,end` |
| `limit` | int | 否 | `100` | 最大节点数 |

**Response `200`**:
```json
{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "ENT_APT_GROUP_a1b2c3d4",
        "name": "APT28",
        "type": "APT_GROUP",
        "group": 1,
        "confidence": 0.95,
        "description": "俄罗斯GRU关联APT组织",
        "properties": {
          "origin_country": "Russia",
          "active_years": "2007-2026",
          "motivation": "espionage",
          "source_count": 47
        }
      },
      {
        "id": "ENT_COUNTRY_b2c3d4e5",
        "name": "Ukraine",
        "type": "COUNTRY",
        "group": 6,
        "description": "目标国家"
      }
    ],
    "edges": [
      {
        "id": "REL_001",
        "source": "ENT_APT_GROUP_a1b2c3d4",
        "target": "ENT_MALWARE_e5f6a7b8",
        "type": "USES",
        "label": "使用",
        "confidence": 0.85,
        "source_text": "APT28利用LameHug恶意软件攻击乌克兰"
      }
    ]
  }
}
```

**节点类型分组对照表**:

| 实体类型 | group | 建议颜色 |
|----------|-------|---------|
| `APT_GROUP` | 1 | `#e74c3c` 红色 |
| `MALWARE` | 2 | `#e67e22` 橙色 |
| `TOOL` | 3 | `#f1c40f` 黄色 |
| `CVE` | 4 | `#9b59b6` 紫色 |
| `TECHNIQUE` | 5 | `#3498db` 蓝色 |
| `COUNTRY` | 6 | `#2ecc71` 绿色 |
| `INDUSTRY` | 7 | `#1abc9c` 青色 |
| `PERSON` | 8 | `#e91e63` 粉色 |
| `CAMPAIGN` | 9 | `#795548` 棕色 |
| `ORGANIZATION` | 10 | `#607d8b` 灰蓝 |

### 3.2 实体展开（爆炸图）

获取以某实体为中心的局部子图。

```
GET /api/v1/graph/expand/:entity_id
```

**Query Parameters**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `depth` | int | 否 | `1` | 展开深度，仅限1层 |
| `relation_types` | string | 否 | - | 按关系类型过滤 |

**Response**: 同 [3.1](#31-获取图数据) 的响应格式，返回以目标实体为中心的新增节点和边

**前端交互说明**:
> 前端调用此接口实现"点击节点→展开关联"功能。返回的数据应与当前图谱合并（而非替换），去重依据为节点`id`和边的`id`。

### 3.3 时间轴过滤

按时间范围过滤图谱数据。

```
GET /api/v1/graph/timeline
```

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `start_date` | string | 是 | 起始日期，格式 `YYYY-MM-DD` |
| `end_date` | string | 是 | 结束日期 |
| `entity_id` | string | 否 | 中心实体（可选） |

**Response**: 同 [3.1](#31-获取图数据) 响应格式

---

## 4. 实体接口

### 4.1 搜索实体

```
GET /api/v1/entities/search
```

**Query Parameters**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `q` | string | 是 | - | 关键词 |
| `type` | string | 否 | - | 实体类型过滤 |
| `page` | int | 否 | `1` | 页码 |
| `page_size` | int | 否 | `20` | 每页条数 |

**Response `200`**:
```json
{
  "success": true,
  "data": {
    "total": 15,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "id": "ENT_APT_GROUP_a1b2c3d4",
        "name": "APT28",
        "type": "APT_GROUP",
        "aliases": ["Fancy Bear", "Sofacy", "Sednit"],
        "description": "与俄罗斯GRU有关联的APT组织",
        "confidence": 0.95
      }
    ]
  }
}
```

### 4.2 获取实体详情

```
GET /api/v1/entities/:entity_id
```

**Response `200`**:
```json
{
  "success": true,
  "data": {
    "id": "ENT_APT_GROUP_a1b2c3d4",
    "name": "APT28",
    "type": "APT_GROUP",
    "aliases": ["Fancy Bear", "Sofacy", "Sednit"],
    "origin_country": "Russia",
    "active_years": "2007-2026",
    "motivation": "espionage",
    "description": "APT28是与俄罗斯总参谋部情报总局（GRU）有关的APT组织",
    "first_seen": "2007-01-01",
    "last_seen": "2026-06-01",
    "confidence": 0.95,
    "source_count": 47,
    "related_campaigns": ["Campaign_A", "Campaign_B"],
    "known_tools": ["LameHug", "X-Agent", "Komplex"],
    "target_sectors": ["government", "military", "energy"]
  }
}
```

### 4.3 获取实体时间线

```
GET /api/v1/entities/:entity_id/timeline
```

**Response `200`**:
```json
{
  "success": true,
  "data": {
    "entity_id": "ENT_APT_GROUP_a1b2c3d4",
    "timeline": [
      { "date": "2007-01-01", "event": "APT28首次被安全厂商发现", "type": "first_seen" },
      { "date": "2015-06-01", "event": "被关联到DNC攻击事件", "type": "campaign" },
      { "date": "2025-03-01", "event": "被发现使用LameHug恶意软件", "type": "tool_usage" },
      { "date": "2026-06-01", "event": "最新一次活跃记录", "type": "last_seen" }
    ]
  }
}
```

---

## 5. 报告接口

### 5.1 生成威胁分析报告

```
GET /api/v1/report
```

**Query Parameters**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `entity_id` | string | 是 | - | 分析目标实体ID |
| `format` | string | 否 | `json` | 输出格式: `json` 或 `markdown` |

**Response `200` (format=json)**:
```json
{
  "success": true,
  "data": {
    "title": "APT28 - 威胁分析报告",
    "generated_at": "2026-07-06T12:00:00Z",
    "summary": "APT28（Fancy Bear）是与俄罗斯GRU有关联的APT组织，自2007年以来持续活跃...",
    "entity_profile": {
      "name": "APT28",
      "aliases": ["Fancy Bear", "Sofacy", "Sednit", "Tsar Team"],
      "origin": "Russia",
      "affiliation": "GRU (Main Intelligence Directorate)",
      "first_seen": "2007",
      "motivation": "政治间谍、地缘政治情报收集"
    },
    "timeline": [
      { "year": "2007", "event": "首次被发现" },
      { "year": "2015-2016", "event": "参与美国大选干预相关黑客活动" },
      { "year": "2025", "event": "使用LameHug恶意软件攻击乌克兰" }
    ],
    "ttp_analysis": [
      {
        "ttp_id": "T1566",
        "name": "鱼叉式钓鱼附件",
        "tactic": "初始访问",
        "description": "APT28常通过鱼叉式钓鱼邮件投递恶意附件",
        "observed_count": 12
      },
      {
        "ttp_id": "T1203",
        "name": "利用客户端漏洞",
        "tactic": "执行",
        "description": "利用Office漏洞执行恶意代码",
        "observed_count": 8
      }
    ],
    "target_analysis": [
      { "target": "乌克兰", "type": "COUNTRY", "intensity": "HIGH" },
      { "target": "政府机构", "type": "INDUSTRY", "intensity": "HIGH" },
      { "target": "军事部门", "type": "INDUSTRY", "intensity": "MEDIUM" },
      { "target": "能源行业", "type": "INDUSTRY", "intensity": "MEDIUM" }
    ],
    "related_entities": [
      { "id": "ENT_GROUP_xxx", "name": "Lazarus", "type": "APT_GROUP", "relation": "不同国家APT组织，战术有相似性" },
      { "id": "ENT_GROUP_yyy", "name": "APT43", "type": "APT_GROUP", "relation": "共享部分基础设施" }
    ],
    "threat_assessment": {
      "overall_level": "HIGH",
      "current_trend": "上升中",
      "prediction": "预计APT28将继续利用地缘政治冲突（如俄乌冲突）进行网络间谍活动",
      "recommendations": [
        "加强对鱼叉式钓鱼邮件的防御",
        "及时修补已知漏洞（重点关注CVE-2025-12345等）",
        "部署针对LameHug恶意软件的检测规则"
      ]
    }
  }
}
```

---

## 6. 系统接口

### 6.1 健康检查

```
GET /api/v1/health
```

**Response `200`**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "components": {
      "llm_api": "connected",
      "neo4j": "connected",
      "storage": "available"
    },
    "uptime_seconds": 86400
  }
}
```

### 6.2 重新处理

重新处理已分析的文档。

```
POST /api/v1/analyze/reprocess/:document_id
```

**Response `200`**:
```json
{
  "success": true,
  "data": {
    "document_id": "a1b2c3d4e5f67890",
    "status": "processing"
  }
}
```

---

## 7. 附录：前端集成指南

### 7.1 开发阶段使用Mock数据

在前端开发阶段，无需等待后端和LLM组完成，直接使用 `mock_data.json` 进行开发和调试。

**步骤**:
1. 前端组从 `mock_data.json` 加载图数据
2. 使用 `/api/v1/graph` 的响应格式直接渲染
3. 后端完成后，将 `mock_data.json` 替换为真实API调用：
   ```javascript
   // 开发阶段
   // const data = mockData;
   
   // 联调阶段
   const response = await fetch('/api/v1/graph?entity_id=ENT_APT_GROUP_a1b2c3d4&depth=2');
   const data = await response.json();
   ```

### 7.2 关键交互实现指引

| 功能 | API | 说明 |
|------|-----|------|
| 搜索实体 | `GET /api/v1/entities/search?q=APT28` | 搜索框输入，返回实体列表 |
| 初次渲染 | `GET /api/v1/graph?entity_id=xxx&depth=2` | 选择实体后加载图谱 |
| 展开节点 | `GET /api/v1/graph/expand/:id?depth=1` | 点击节点，合并新增数据 |
| 时间轴过滤 | `GET /api/v1/graph/timeline?start=2025-01-01&end=2025-12-31` | 拖动时间轴滑块 |
| 实体详情 | `GET /api/v1/entities/:id` | 点击节点弹出详情面板 |
| 生成报告 | `GET /api/v1/report?entity_id=xxx` | 点击"生成报告"按钮 |

### 7.3 请求流程时序

```
前端                        后端/API                      LLM服务                    Neo4j
  |                           |                            |                         |
  |--- POST /analyze -------->|                            |                         |
  |                           |--- LLM抽取请求 ----------->|                         |
  |                           |<--- 实体/关系JSON ---------|                         |
  |                           |--- 写入图谱 -------------->|--------->|              |
  |                           |<-- 写入成功 ---------------|<---------|              |
  |<-- 200 OK ---------------|                            |                         |
  |                           |                            |                         |
  |--- GET /graph ----------->|                            |                         |
  |                           |--- 查询子图 -------------->|--------->|              |
  |                           |<-- 节点+边数据 ------------|<---------|              |
  |<-- 渲染图谱 -------------|                            |                         |
```

### 7.4 常见问题

**Q: 浏览器渲染卡顿怎么办？**
A: 前端默认只渲染2层以内的关系，深层关系使用"点击加载更多"。如果节点超过200个，启用虚拟滚动或WebGL渲染。

**Q: 如何处理加载状态？**
A: 所有API返回前，前端应显示骨架屏或加载动画。`/analyze` 接口可能耗时5-15秒，建议显示进度条。

**Q: 搜索支持中文吗？**
A: 支持。搜索接口对中文进行了优化，支持拼音首字母和模糊匹配。

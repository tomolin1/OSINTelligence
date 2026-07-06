# 黄金测试集格式规范

> **版本**: 1.0 | **维护**: 架构与数据规范组  
> **说明**: 本文定义 `golden.json`（黄金测试集）的格式规范，由数据与样本组负责填写，LLM组据此调优Prompt，测试组据此评估质量。

---

## 1. 文件位置与命名

```
data/golden.json
```

## 2. 整体结构

```json
{
  "meta": {
    "version": "1.0.0",
    "created_at": "2026-07-06",
    "last_updated": "2026-07-06",
    "created_by": "数据与样本组",
    "total_entities": 45,
    "total_relationships": 30,
    "target_groups": ["APT28", "Lazarus", "Kimsuky"],
    "sources": [
      "https://attack.mitre.org/groups/G0007/",
      "https://en.wikipedia.org/wiki/APT28",
      "..."
    ]
  },
  "documents": [
    { ... },
    { ... }
  ],
  "golden_entities": [ ... ],
  "golden_relationships": [ ... ]
}
```

## 3. documents 字段

人工标注的原始文档片段（每段包含已知的实体和关系）：

```json
{
  "id": "doc_001",
  "source": "Wikipedia - APT28",
  "language": "zh",
  "text": "APT28，也被称为Fancy Bear，是一个与俄罗斯总参谋部情报总局（GRU）有关的APT组织。该组织自2007年以来活跃，主要针对政府、军事和能源行业进行网络间谍活动。APT28使用X-Agent恶意软件和鱼叉式钓鱼攻击。",
  "known_entity_ids": ["ent_gold_apt28", "ent_gold_fancybear", "ent_gold_gru", "ent_gold_xagent"],
  "known_relation_ids": ["rel_gold_apt28_gru", "rel_gold_apt28_xagent"]
}
```

## 4. golden_entities 字段

每个实体包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 唯一ID，格式: `ent_gold_{name}` |
| `name` | string | 是 | 标准名称 |
| `type` | string | 是 | 实体类型枚举（见schema.json） |
| `aliases` | string[] | 否 | 别名列表 |
| `description` | string | 是 | 描述 |
| `verified` | boolean | 是 | 是否经人工核实 |
| `source` | string | 是 | 信息来源 |

**示例**:
```json
{
  "id": "ent_gold_apt28",
  "name": "APT28",
  "type": "APT_GROUP",
  "aliases": ["Fancy Bear", "Sofacy", "Sednit", "Tsar Team"],
  "description": "与俄罗斯GRU有关联的APT组织",
  "verified": true,
  "source": "MITRE ATT&CK G0007"
}
```

## 5. golden_relationships 字段

每条关系包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 唯一ID, 格式: `rel_gold_{description}` |
| `source_id` | string | 是 | 主体实体ID |
| `target_id` | string | 是 | 客体实体ID |
| `type` | string | 是 | 关系类型枚举（见schema.json） |
| `description` | string | 否 | 关系描述 |
| `verified` | boolean | 是 | 是否经人工核实 |
| `source` | string | 是 | 信息来源 |

**示例**:
```json
{
  "id": "rel_gold_apt28_gru",
  "source_id": "ent_gold_apt28",
  "target_id": "ent_gold_gru",
  "type": "ATTRIBUTED_TO",
  "description": "APT28归属于俄罗斯GRU",
  "verified": true,
  "source": "公开威胁情报报告"
}
```

## 6. 各目标组织的最低标注要求

| 目标组织 | 最少实体数 | 最少关系数 | 重点实体类型 |
|----------|-----------|-----------|-------------|
| APT28 | 12 | 10 | APT_GROUP, MALWARE, CVE, TECHNIQUE, COUNTRY, ORGANIZATION |
| Lazarus | 12 | 10 | APT_GROUP, MALWARE, CVE, TECHNIQUE, INDUSTRY, CAMPAIGN |
| Kimsuky | 10 | 8 | APT_GROUP, MALWARE, TECHNIQUE, COUNTRY, CAMPAIGN |

## 7. 评估指标

LLM组应使用golden.json进行Prompt调优，测试组应每日报告以下指标：

```
准确率 (Precision) = 正确提取的实体数 / 总提取实体数
召回率 (Recall)     = 正确提取的实体数 / 黄金集中的实体总数
F1分数              = 2 * (Precision * Recall) / (Precision + Recall)
关系准确率          = 正确提取的关系数 / 总提取关系数
```

> **仅此格式定义归架构组所有，golden.json的数据内容由数据与样本组负责填写。**

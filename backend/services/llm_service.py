"""
LLM 抽取服务
"""

import json
import hashlib
import logging
from datetime import datetime

import httpx

from backend.config import (
    LLM_API_KEY, LLM_MODEL, LLM_API_BASE,
    LLM_MAX_RETRIES, LLM_TIMEOUT, PIPELINE_VERSION
)
from backend.models import LLMExtractionOutput, Entity, Relationship, Summary, Mention

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业威胁情报实体关系抽取助手。从给定的情报文本中提取威胁情报相关的实体和关系。

## 实体类型
- APT_GROUP: APT组织
- MALWARE: 恶意软件
- TOOL: 攻击工具
- CVE: 漏洞编号
- TECHNIQUE: MITRE ATT&CK技术
- PERSON: 人员
- COUNTRY: 国家
- INDUSTRY: 行业
- CAMPAIGN: 攻击活动
- ORGANIZATION: 通用组织
- TIME: 时间实体

## 关系类型
- ATTRIBUTED_TO: 归因于
- USES: 使用
- TARGETS: 瞄准
- DEVELOPS: 开发
- EXPLOITS: 利用漏洞
- RELATED_TO: 通用关联
- AFFILIATED_WITH: 组织间关联
- LEADS_TO: 攻击链顺序
- DISCOVERED_BY: 被发现
- EMPLOYS: 雇佣

## 输出要求
你必须输出合法的 JSON，格式如下：
{
  "entities": [
    {
      "id": "ENT_{TYPE}_{HASH}",
      "name": "实体名称",
      "type": "实体类型枚举",
      "aliases": ["别名1"],
      "description": "实体描述",
      "source_text": "原文引用片段",
      "confidence": 0.0~1.0
    }
  ],
  "relationships": [
    {
      "id": "REL_{HASH}",
      "source_id": "主体实体ID",
      "target_id": "客体实体ID",
      "type": "关系类型枚举",
      "description": "关系描述",
      "source_text": "原文证据",
      "confidence": 0.0~1.0
    }
  ],
  "summary": {
    "overview": "概述",
    "key_findings": ["发现1", "发现2"],
    "threat_level": "HIGH/MEDIUM/LOW",
    "relevant_ttps": ["T1566"]
  }
}

只输出 JSON，不要任何额外文字。确保 JSON 合法。"""


class LLMService:
    """LLM 抽取服务"""

    async def extract(
        self, text: str, source_url: str = "",
        language: str = "zh"
    ) -> LLMExtractionOutput:
        """从文本中提取实体和关系"""
        document_id = hashlib.md5(source_url.encode()).hexdigest()[:16]

        content = f"## 来源\n{source_url}\n\n## 文本\n{text}"
        if language == "zh":
            content = f"## 来源\n{source_url}\n\n## 文本\n{text}"

        last_error = None
        for attempt in range(LLM_MAX_RETRIES):
            try:
                raw = await self._call_llm(content)
                data = json.loads(raw)
                return self._parse_response(document_id, data, source_url)
            except json.JSONDecodeError as e:
                last_error = e
                logger.warning("LLM 输出非合法 JSON (第%d次重试): %s", attempt + 1, e)
                continue
            except Exception as e:
                last_error = e
                logger.error("LLM 调用异常 (第%d次重试): %s", attempt + 1, e)
                continue

        logger.error("LLM 抽取失败，已达最大重试次数: %s", last_error)
        return LLMExtractionOutput(document_id=document_id, pipeline_version=PIPELINE_VERSION)

    async def _call_llm(self, content: str) -> str:
        """调用大模型 API"""
        headers = {
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            response = await client.post(
                f"{LLM_API_BASE}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]

    def _parse_response(
        self, document_id: str, data: dict, source_url: str = ""
    ) -> LLMExtractionOutput:
        """解析LLM返回数据"""
        entities = []
        for e in data.get("entities", []):
            mentions = []
            if "mentions" in e:
                mentions = [Mention(**m) for m in e["mentions"]]
            entities.append(Entity(
                id=e.get("id", f"ENT_UNKNOWN"),
                name=e.get("name", ""),
                type=e.get("type", "ORGANIZATION"),
                aliases=e.get("aliases", []),
                description=e.get("description", ""),
                source_text=e.get("source_text", ""),
                confidence=min(float(e.get("confidence", 0.5)), 1.0),
                mentions=mentions,
            ))

        relationships = []
        for r in data.get("relationships", []):
            relationships.append(Relationship(
                id=r.get("id", f"REL_{document_id}"),
                source_id=r.get("source_id", ""),
                target_id=r.get("target_id", ""),
                type=r.get("type", "RELATED_TO"),
                description=r.get("description", ""),
                source_text=r.get("source_text", ""),
                confidence=min(float(r.get("confidence", 0.5)), 1.0),
                mitre_attack_id=r.get("mitre_attack_id"),
            ))

        summary_data = data.get("summary", {})
        summary = Summary(
            overview=summary_data.get("overview", ""),
            key_findings=summary_data.get("key_findings", []),
            threat_level=summary_data.get("threat_level", "MEDIUM"),
            relevant_ttps=summary_data.get("relevant_ttps", []),
        )

        return LLMExtractionOutput(
            document_id=document_id,
            entities=entities,
            relationships=relationships,
            summary=summary,
            analysis_time=datetime.utcnow(),
            pipeline_version=PIPELINE_VERSION,
            source_url=source_url,
        )


# 全局单例
llm_svc = LLMService()

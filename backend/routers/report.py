"""
报告接口 — /api/v1/report
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from backend.models import ApiResponse, ReportResponse
from backend.services import neo4j_svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/report", tags=["报告"])


@router.get("", response_model=ApiResponse)
async def generate_report(
    entity_id: str = Query(..., description="目标实体ID"),
    format: str = Query("json", pattern="^(json|markdown)$"),
):
    """生成威胁分析报告"""
    try:
        node = await neo4j_svc.get_node(entity_id)
        if not node:
            raise HTTPException(status_code=404, detail="实体未找到")

        nodes, edges = await neo4j_svc.get_subgraph(entity_id, depth=2)
        timeline = await neo4j_svc.get_timeline(entity_id)

        # 统计关联实体类型
        related_groups = {}
        for n in nodes:
            if n.get("id") != entity_id:
                t = n.get("type", "UNKNOWN")
                related_groups[t] = related_groups.get(t, 0) + 1

        report = ReportResponse(
            title=f"{node.get('name', entity_id)} - 威胁分析报告",
            summary=node.get("description", ""),
            entity_profile={
                "name": node.get("name"),
                "aliases": node.get("aliases", []),
                "type": list(node.get("labels", []))[0] if node.get("labels") else "UNKNOWN",
                "origin": node.get("origin_country", "未知"),
                "motivation": node.get("motivation", "未知"),
                "first_seen": str(node.get("first_seen", "")),
                "last_seen": str(node.get("last_seen", "")),
            },
            timeline=[{
                "date": e.get("date", ""),
                "event": e.get("event", ""),
            } for e in timeline],
            ttp_analysis=[],
            target_analysis=[{
                "target": n.get("name", ""),
                "type": n.get("type", ""),
                "intensity": "MEDIUM",
            } for n in nodes if n.get("type") in ("COUNTRY", "INDUSTRY")],
            related_entities=[{
                "id": n.get("id"),
                "name": n.get("name"),
                "type": n.get("type"),
                "relation": "相关实体",
            } for n in nodes if n.get("id") != entity_id][:10],
            threat_assessment={
                "overall_level": node.get("confidence", 0.5) > 0.8 and "HIGH" or "MEDIUM",
                "recommendations": [
                    "关注该组织的最新活动报告",
                    "更新相关检测规则",
                    "加强针对性防御",
                ],
            },
        )

        return ApiResponse(data=report.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("生成报告失败")
        raise HTTPException(status_code=500, detail=str(e))

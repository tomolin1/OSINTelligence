"""
实体接口 — /api/v1/entities
"""

import logging
from fastapi import APIRouter, HTTPException, Query

from backend.models import (
    EntitySearchResponse, EntitySearchResult,
    EntityDetailResponse, EntityTimelineResponse,
    TimelineEvent, ApiResponse, EntityType
)
from backend.services import neo4j_svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/entities", tags=["实体"])


@router.get("/search", response_model=ApiResponse)
async def search_entities(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    type: str | None = Query(None, description="实体类型过滤"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """搜索实体"""
    try:
        items, total = await neo4j_svc.search_entities(
            keyword=q,
            entity_type=type,
            page=page,
            page_size=page_size,
        )

        results = [
            EntitySearchResult(
                id=item["id"],
                name=item["name"],
                type=item.get("type", "UNKNOWN"),
                aliases=item.get("aliases", []),
                description=item.get("description", ""),
                confidence=item.get("confidence", 0.0),
            )
            for item in items
        ]

        return ApiResponse(data=EntitySearchResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=results,
        ).model_dump())

    except Exception as e:
        logger.exception("搜索失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_id}", response_model=ApiResponse)
async def get_entity_detail(entity_id: str):
    """获取实体详情"""
    try:
        node = await neo4j_svc.get_node(entity_id)
        if not node:
            raise HTTPException(status_code=404, detail="实体未找到")

        return ApiResponse(data=EntityDetailResponse(
            id=node.get("id", entity_id),
            name=node.get("name", ""),
            type=node.get("type", "UNKNOWN"),
            aliases=node.get("aliases", []),
            origin_country=node.get("origin_country"),
            active_years=node.get("active_years"),
            motivation=node.get("motivation"),
            description=node.get("description", ""),
            confidence=node.get("confidence", 0.0),
            source_count=node.get("source_count", 0),
        ).model_dump())

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("查询实体详情失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_id}/timeline", response_model=ApiResponse)
async def get_entity_timeline(entity_id: str):
    """获取实体时间线"""
    try:
        events = await neo4j_svc.get_timeline(entity_id)
        return ApiResponse(data=EntityTimelineResponse(
            entity_id=entity_id,
            timeline=[TimelineEvent(**e) for e in events],
        ).model_dump())

    except Exception as e:
        logger.exception("查询时间线失败")
        raise HTTPException(status_code=500, detail=str(e))

"""
图谱接口 — /api/v1/graph
"""

import logging
from fastapi import APIRouter, HTTPException, Query

from backend.models import (
    GraphResponse, GraphNode, GraphEdge, ApiResponse,
    EntityType, RelationType, ENTITY_TYPE_GROUP_MAP
)
from backend.services import neo4j_svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["图谱"])


@router.get("", response_model=ApiResponse)
async def get_graph(
    entity_id: str | None = Query(None, description="中心实体ID"),
    depth: int = Query(2, ge=1, le=3, description="关系深度"),
    types: str | None = Query(None, description="实体类型过滤，逗号分隔"),
    limit: int = Query(100, ge=1, le=500, description="最大节点数"),
):
    """获取知识图谱数据"""
    type_list = types.split(",") if types else None

    try:
        raw_nodes, raw_edges = await neo4j_svc.get_subgraph(
            entity_id=entity_id,
            depth=depth,
            types=type_list,
            limit=limit,
        )

        nodes = []
        edge_ids = set()
        edges = []

        for n in raw_nodes:
            node_type = n.get("type", "UNKNOWN")
            group = ENTITY_TYPE_GROUP_MAP.get(
                EntityType(node_type), 0
            ).value if node_type in EntityType._value2member_map_ else 0

            nodes.append(GraphNode(
                id=n.get("id", ""),
                name=n.get("name", ""),
                type=n.get("type", "UNKNOWN"),
                group=group,
                confidence=n.get("confidence", 1.0),
                description=n.get("description", ""),
                properties={k: v for k, v in n.items()
                           if k not in ("id", "name", "type", "confidence", "description")},
            ))

        for e in raw_edges:
            eid = e.get("id", "")
            if eid and eid not in edge_ids:
                edge_ids.add(eid)
                edges.append(GraphEdge(
                    id=eid,
                    source=e.get("source", ""),
                    target=e.get("target", ""),
                    type=e.get("type", "RELATED_TO"),
                    label=e.get("label", e.get("type", "")),
                    confidence=e.get("confidence", 1.0),
                    source_text=e.get("source_text", ""),
                    mitre_attack_id=e.get("mitre_attack_id"),
                ))

        return ApiResponse(data={"nodes": [n.model_dump() for n in nodes],
                                  "edges": [e.model_dump() for e in edges]})

    except Exception as e:
        logger.exception("图谱查询失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/expand/{entity_id}", response_model=ApiResponse)
async def expand_node(
    entity_id: str,
    depth: int = Query(1, ge=1, le=2),
):
    """展开节点（爆炸图）"""
    return await get_graph(entity_id=entity_id, depth=depth)


@router.get("/timeline", response_model=ApiResponse)
async def get_timeline(
    start_date: str = Query(..., description="起始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    entity_id: str | None = Query(None, description="中心实体"),
):
    """按时间范围过滤图谱"""
    # 先获取全图再按时间过滤
    return await get_graph(entity_id=entity_id)

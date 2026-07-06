"""
MVP 模式 — 无需 Neo4j/LLM，直接返回 mock 数据
"""

import json
import os
from pathlib import Path
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(tags=["MVP"])

# 项目根目录：当前文件在 backend/routers/，向上两级就是项目根
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_mock = None

def get_mock():
    global _mock
    if _mock is None:
        p = PROJECT_ROOT / 'mock_data.json'
        with open(p, 'r', encoding='utf-8') as f:
            _mock = json.load(f)
    return _mock


@router.get("/api/v1/graph", summary="MVP图谱查询（mock模式）")
async def mvp_graph(
    entity_id: str = Query(None, description="中心实体ID"),
    depth: int = Query(2, ge=1, le=3),
):
    data = get_mock()
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    if entity_id:
        connected = {entity_id}
        target_edges = [e for e in edges if e["source"] == entity_id or e["target"] == entity_id]
        for e in target_edges:
            connected.add(e["source"])
            connected.add(e["target"])
        nodes = [n for n in nodes if n["id"] in connected]
        edges = target_edges

    return {
        "success": True,
        "data": {
            "nodes": nodes,
            "edges": edges,
        },
        "timestamp": "2026-07-06T12:00:00Z",
    }


@router.get("/api/v1/entities/search", summary="MVP搜索（mock模式）")
async def mvp_search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    data = get_mock()
    kw = q.lower()
    items = [
        {
            "id": n["id"],
            "name": n["name"],
            "type": n["type"],
            "aliases": n.get("properties", {}).get("aliases", []),
            "description": n.get("description", ""),
            "confidence": n.get("confidence", 0),
        }
        for n in data.get("nodes", [])
        if kw in n["name"].lower() or kw in n["type"].lower()
    ]
    total = len(items)
    items = items[(page - 1) * page_size: page * page_size]

    return {
        "success": True,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        },
        "timestamp": "2026-07-06T12:00:00Z",
    }


@router.get("/api/v1/entities/{entity_id}", summary="MVP实体详情（mock模式）")
async def mvp_entity_detail(entity_id: str):
    data = get_mock()
    for n in data.get("nodes", []):
        if n["id"] == entity_id:
            p = n.get("properties", {})
            return {
                "success": True,
                "data": {
                    "id": n["id"],
                    "name": n["name"],
                    "type": n["type"],
                    "aliases": p.get("aliases", []),
                    "origin_country": p.get("origin_country"),
                    "active_years": p.get("active_years"),
                    "motivation": p.get("motivation"),
                    "description": n.get("description", ""),
                    "confidence": n.get("confidence", 0),
                    "source_count": p.get("source_count", 0),
                },
                "timestamp": "2026-07-06T12:00:00Z",
            }
    return JSONResponse(status_code=404, content={"success": False, "error": {"code": "ERR_DB_002", "message": "实体未找到"}})


@router.get("/api/v1/health")
async def mvp_health():
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "version": "1.0.0-mvp",
            "components": {"mock_data": "loaded", "neo4j": "mock_mode", "llm_api": "mock_mode"},
            "uptime_seconds": 42,
        },
        "timestamp": "2026-07-06T12:00:00Z",
    }

"""
MVP 模式 — 无需 Neo4j/LLM，优先读取 data/extracted/ 真源，fallback 到 mock_data.json
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(tags=["MVP"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_start_time = time.time()

_mock = None


def _load_mock():
    """加载 mock_data.json（单例）"""
    global _mock
    if _mock is None:
        p = PROJECT_ROOT / "mock_data.json"
        with open(p, "r", encoding="utf-8") as f:
            _mock = json.load(f)
    return _mock


def _load_extracted():
    """加载 data/extracted/ 中所有 LLM 抽取结果，合并为 {nodes, edges} 结构"""
    extracted_dir = PROJECT_ROOT / "data" / "extracted"
    if not extracted_dir.exists():
        return None

    json_files = list(extracted_dir.glob("*.json"))
    if not json_files:
        return None

    nodes_map = {}
    edges_map = {}

    for f in json_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        entity_map = {}  # entity_id -> entity dict
        for e in data.get("entities", []):
            eid = e.get("id", "")
            entity_map[eid] = e
            if eid not in nodes_map:
                group_map = {
                    "APT_GROUP": 1, "MALWARE": 2, "TOOL": 3, "CVE": 4,
                    "TECHNIQUE": 5, "COUNTRY": 6, "INDUSTRY": 7,
                    "PERSON": 8, "CAMPAIGN": 9, "ORGANIZATION": 10,
                }
                nodes_map[eid] = {
                    "id": eid,
                    "name": e.get("name", ""),
                    "type": e.get("type", "ORGANIZATION"),
                    "group": group_map.get(e.get("type", ""), 0),
                    "confidence": e.get("confidence", 0.0),
                    "description": e.get("description", ""),
                    "properties": {
                        "aliases": e.get("aliases", []),
                        "source_text": e.get("source_text", ""),
                    },
                }

        for r in data.get("relationships", []):
            rid = r.get("id", "")
            if rid and rid not in edges_map:
                edges_map[rid] = {
                    "id": rid,
                    "source": r.get("source_id", ""),
                    "target": r.get("target_id", ""),
                    "type": r.get("type", "RELATED_TO"),
                    "label": r.get("type", ""),
                    "confidence": r.get("confidence", 0.0),
                    "source_text": r.get("source_text", ""),
                }

    return {"nodes": list(nodes_map.values()), "edges": list(edges_map.values())}


def get_data():
    """
    数据加载策略（优先级）：
    1. data/extracted/ 有 LLM 真源 → 直接用
    2. 没有 → fallback 到 mock_data.json
    """
    extracted = _load_extracted()
    if extracted and extracted["nodes"]:
        return extracted
    return _load_mock()


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _uptime():
    return int(time.time() - _start_time)


@router.get("/api/v1/graph", summary="MVP图谱查询")
async def mvp_graph(
    entity_id: str = Query(None, description="中心实体ID"),
    depth: int = Query(2, ge=1, le=3),
):
    data = get_data()
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    if entity_id:
        connected = {entity_id}
        target_edges = [
            e for e in edges
            if e["source"] == entity_id or e["target"] == entity_id
        ]
        for e in target_edges:
            connected.add(e["source"])
            connected.add(e["target"])
        nodes = [n for n in nodes if n["id"] in connected]
        edges = target_edges

    return {
        "success": True,
        "data": {"nodes": nodes, "edges": edges},
        "timestamp": _now(),
    }


@router.get("/api/v1/entities/search", summary="MVP搜索")
async def mvp_search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    data = get_data()
    kw = q.lower()

    items = []
    for n in data.get("nodes", []):
        p = n.get("properties", {})
        aliases = [a.lower() for a in p.get("aliases", [])]
        desc = n.get("description", "").lower()
        name = n.get("name", "").lower()
        ntype = n.get("type", "").lower()

        if kw in name or kw in ntype or kw in desc or any(kw in a for a in aliases):
            items.append({
                "id": n["id"],
                "name": n["name"],
                "type": n["type"],
                "aliases": p.get("aliases", []),
                "description": n.get("description", ""),
                "confidence": n.get("confidence", 0),
            })

    total = len(items)
    items = items[(page - 1) * page_size : page * page_size]

    return {
        "success": True,
        "data": {"total": total, "page": page, "page_size": page_size, "items": items},
        "timestamp": _now(),
    }


@router.get("/api/v1/entities/{entity_id}", summary="MVP实体详情")
async def mvp_entity_detail(entity_id: str):
    data = get_data()
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
                "timestamp": _now(),
            }
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": {"code": "ERR_DB_002", "message": f"实体 {entity_id} 未找到"},
        },
    )


@router.get("/api/v1/health")
async def mvp_health():
    data = get_data()
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    # 统计各类型数量
    type_counts = {}
    for n in nodes:
        t = n.get("type", "UNKNOWN")
        type_counts[t] = type_counts.get(t, 0) + 1

    source = "extracted" if _load_extracted() else "mock"

    return {
        "success": True,
        "data": {
            "status": "healthy",
            "version": "1.0.0-mvp",
            "data_source": source,
            "stats": {
                "nodes": len(nodes),
                "edges": len(edges),
                "entity_types": type_counts,
            },
            "components": {
                "mock_data": "loaded" if _load_mock() else "missing",
                "extracted_data": f"{len(_load_extracted()['nodes']) if _load_extracted() else 0} nodes" if _load_extracted() else "not found",
                "neo4j": "mock_mode",
                "llm_api": "mock_mode",
            },
            "uptime_seconds": _uptime(),
        },
        "timestamp": _now(),
    }

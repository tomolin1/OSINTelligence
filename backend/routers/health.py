"""
系统接口 — /api/v1/health
"""

import time
import logging
from fastapi import APIRouter

from backend.models import ApiResponse, HealthResponse
from backend.services import neo4j_svc

logger = logging.getLogger(__name__)
router = APIRouter(tags=["系统"])

START_TIME = time.time()


@router.get("/health", response_model=ApiResponse)
async def health_check():
    """健康检查"""
    neo4j_ok = await neo4j_svc.check_health()

    return ApiResponse(data=HealthResponse(
        status="healthy" if neo4j_ok else "degraded",
        components={
            "neo4j": "connected" if neo4j_ok else "disconnected",
            "llm_api": "configured",
            "storage": "available",
        },
        uptime_seconds=int(time.time() - START_TIME),
    ).model_dump())

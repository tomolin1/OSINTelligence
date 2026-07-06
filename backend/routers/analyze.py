"""
分析接口 — /api/v1/analyze
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from backend.config import (
    CRAWLER_OUTPUT_DIR, PROCESSED_MARK_DIR,
    MAX_FILE_SIZE, MAX_TEXT_LENGTH, MIN_TEXT_LENGTH
)
from backend.models import (
    AnalyzeRequest, LLMExtractionOutput,
    BatchAnalyzeRequest, BatchAnalyzeResponse,
    AnalyzeStatusResponse, ApiResponse, ApiErrorResponse,
    CrawlerOutput
)
from backend.services import neo4j_svc, llm_svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["分析"])


@router.post("", response_model=ApiResponse)
async def analyze_document(req: AnalyzeRequest):
    """提交文本进行LLM实体关系抽取"""
    try:
        result = await llm_svc.extract(
            text=req.text,
            source_url=req.source_url,
            language=req.language or "zh",
        )

        # 自动存入 Neo4j
        for entity in result.entities:
            label = entity.type.value
            await neo4j_svc.merge_node(label, entity.id, entity.model_dump())

        for rel in result.relationships:
            await neo4j_svc.create_relationship(
                rel.source_id, rel.target_id,
                rel.type.value, rel.model_dump()
            )

        return ApiResponse(data=result.model_dump())
    except Exception as e:
        logger.exception("分析失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/file", response_model=ApiResponse)
async def analyze_file(file: UploadFile = File(...)):
    """上传文件进行LLM抽取"""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过10MB限制")

    text = content.decode("utf-8")

    # 如果是JSON格式的爬虫输出，提取raw_text
    if file.filename.endswith(".json"):
        try:
            data = json.loads(text)
            if "raw_text" in data:
                text = data["raw_text"]
            source_url = data.get("source_url", file.filename or "unknown")
        except json.JSONDecodeError:
            source_url = file.filename or "unknown"
    else:
        source_url = file.filename or "unknown"

    if len(text) < MIN_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail="文本内容太少")
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    result = await llm_svc.extract(text, source_url=source_url)
    return ApiResponse(data=result.model_dump())


@router.post("/batch", response_model=ApiResponse)
async def batch_analyze(req: BatchAnalyzeRequest):
    """批量分析目录下所有爬虫输出文件"""
    crawl_dir = Path(req.directory)
    if not crawl_dir.exists():
        raise HTTPException(status_code=400, detail="目录不存在")

    mark_dir = Path(PROCESSED_MARK_DIR)
    if req.resume:
        mark_dir.mkdir(parents=True, exist_ok=True)

    json_files = list(crawl_dir.glob("*.json"))
    response = BatchAnalyzeResponse(total_files=len(json_files))

    for f in json_files:
        mark_file = mark_dir / f"{f.stem}.done"
        if req.resume and mark_file.exists():
            response.skipped += 1
            continue

        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            text = data.get("raw_text", "") if isinstance(data, dict) else data
            source_url = data.get("source_url", f.name) if isinstance(data, dict) else f.name

            if len(text) < MIN_TEXT_LENGTH:
                response.skipped += 1
                continue

            result = await llm_svc.extract(text, source_url=source_url)

            for entity in result.entities:
                await neo4j_svc.merge_node(entity.type.value, entity.id, entity.model_dump())
            for rel in result.relationships:
                await neo4j_svc.create_relationship(
                    rel.source_id, rel.target_id,
                    rel.type.value, rel.model_dump()
                )

            response.processed += 1
            if req.resume:
                mark_file.write_text(datetime.utcnow().isoformat())

        except Exception as e:
            logger.error("文件处理失败: %s, %s", f.name, e)
            response.failed += 1
            response.errors.append({"file": f.name, "error": str(e)})

    return ApiResponse(data=response.model_dump())


@router.get("/status/{document_id}", response_model=ApiResponse)
async def get_analyze_status(document_id: str):
    """查询分析状态"""
    status = AnalyzeStatusResponse(
        document_id=document_id,
        status="completed",
        progress=1.0,
    )
    return ApiResponse(data=status.model_dump())

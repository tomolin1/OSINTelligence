"""
分析接口 — /api/v1/analyze
"""

import json
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from backend.config import (
    CRAWLER_OUTPUT_DIR, PROCESSED_MARK_DIR,
    MAX_FILE_SIZE, MAX_TEXT_LENGTH, MIN_TEXT_LENGTH,
    LLM_MAX_CONCURRENCY
)
from backend.models import (
    AnalyzeRequest, LLMExtractionOutput,
    BatchAnalyzeRequest, BatchAnalyzeResponse,
    AnalyzeStatusResponse, ApiResponse, ApiErrorResponse,
    CrawlerOutput, validate_extraction
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

        # Schema 校验：拒绝不合法数据，防止脏数据写入 Neo4j
        validation_errors = validate_extraction(result)
        if validation_errors:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "LLM 抽取结果校验失败",
                    "errors": [e.model_dump() for e in validation_errors],
                }
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

    # Schema 校验
    validation_errors = validate_extraction(result)
    if validation_errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "LLM 抽取结果校验失败",
                "errors": [e.model_dump() for e in validation_errors],
            }
        )

    return ApiResponse(data=result.model_dump())


@router.post("/batch", response_model=ApiResponse)
async def batch_analyze(req: BatchAnalyzeRequest):
    """批量分析目录下所有爬虫输出文件（并发处理）"""
    crawl_dir = Path(req.directory)
    if not crawl_dir.exists():
        raise HTTPException(status_code=400, detail="目录不存在")

    mark_dir = Path(PROCESSED_MARK_DIR)
    if req.resume:
        mark_dir.mkdir(parents=True, exist_ok=True)

    json_files = list(crawl_dir.glob("*.json"))
    response = BatchAnalyzeResponse(total_files=len(json_files))
    semaphore = asyncio.Semaphore(LLM_MAX_CONCURRENCY)

    async def process_one(f: Path) -> dict | None:
        """处理单个文件，返回 None 表示跳过，返回 dict 表示错误"""
        mark_file = mark_dir / f"{f.stem}.done"
        if req.resume and mark_file.exists():
            return None  # 跳过

        async with semaphore:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                text = data.get("raw_text", "") if isinstance(data, dict) else data
                source_url = data.get("source_url", f.name) if isinstance(data, dict) else f.name

                if len(text) < MIN_TEXT_LENGTH:
                    return None  # 跳过

                result = await llm_svc.extract(text, source_url=source_url)

                # Schema 校验
                validation_errors = validate_extraction(result)
                if validation_errors:
                    return {
                        "file": f.name,
                        "error": "校验失败",
                        "validation_errors": [e.model_dump() for e in validation_errors],
                    }

                for entity in result.entities:
                    await neo4j_svc.merge_node(entity.type.value, entity.id, entity.model_dump())
                for rel in result.relationships:
                    await neo4j_svc.create_relationship(
                        rel.source_id, rel.target_id,
                        rel.type.value, rel.model_dump()
                    )

                if req.resume:
                    mark_file.write_text(datetime.utcnow().isoformat())

                return {"ok": True}

            except Exception as e:
                logger.error("文件处理失败: %s, %s", f.name, e)
                return {"file": f.name, "error": str(e)}

    results = await asyncio.gather(*[process_one(f) for f in json_files])

    for r in results:
        if r is None:
            response.skipped += 1
        elif r.get("ok"):
            response.processed += 1
        else:
            response.failed += 1
            response.errors.append(r)

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

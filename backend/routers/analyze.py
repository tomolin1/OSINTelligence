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
    EXTRACTED_OUTPUT_DIR, PIPELINE_VERSION,
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


def _save_extraction_to_disk(result: LLMExtractionOutput):
    """将 LLM 抽取结果持久化到文件系统（唯一真源）"""
    out_dir = Path(EXTRACTED_OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    filepath = out_dir / f"{result.document_id}.json"
    filepath.write_text(
        result.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("抽取结果已保存: %s", filepath)


async def _write_to_neo4j(result: LLMExtractionOutput):
    """将抽取结果写入 Neo4j（查询缓存层）"""
    for entity in result.entities:
        label = entity.type.value
        props = entity.model_dump()
        props["pipeline_version"] = result.pipeline_version
        await neo4j_svc.merge_node(label, entity.id, props)

    for rel in result.relationships:
        props = rel.model_dump()
        props["pipeline_version"] = result.pipeline_version
        await neo4j_svc.create_relationship(
            rel.source_id, rel.target_id,
            rel.type.value, props
        )


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

        # 写入真源（文件系统），再写入缓存（Neo4j）
        _save_extraction_to_disk(result)
        await _write_to_neo4j(result)

        return ApiResponse(data=result.model_dump())
    except HTTPException:
        raise
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

    _save_extraction_to_disk(result)
    await _write_to_neo4j(result)

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

                # 先写真源（文件），再写缓存（Neo4j）
                _save_extraction_to_disk(result)
                await _write_to_neo4j(result)

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


@router.post("/rebuild", response_model=ApiResponse)
async def rebuild_neo4j():
    """从 data/extracted/ 中的 JSON 真源重建 Neo4j 图谱缓存。
    适用场景：Prompt 迭代后重跑、Neo4j 数据损坏恢复。
    """
    extracted_dir = Path(EXTRACTED_OUTPUT_DIR)
    if not extracted_dir.exists():
        raise HTTPException(status_code=400, detail="extracted 目录不存在，请先运行抽取")

    json_files = list(extracted_dir.glob("*.json"))
    if not json_files:
        raise HTTPException(status_code=400, detail="extracted 目录为空，无数据可重建")

    try:
        await neo4j_svc.clear_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空 Neo4j 失败: {e}")

    semaphore = asyncio.Semaphore(10)

    async def rebuild_one(f: Path) -> dict | None:
        async with semaphore:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                result = LLMExtractionOutput(**data)
                await _write_to_neo4j(result)
                return {"ok": True}
            except Exception as e:
                logger.error("重建失败: %s, %s", f.name, e)
                return {"file": f.name, "error": str(e)}

    results = await asyncio.gather(*[rebuild_one(f) for f in json_files])
    processed = sum(1 for r in results if r and r.get("ok"))
    failed = sum(1 for r in results if r and not r.get("ok"))

    return ApiResponse(data={
        "message": "Neo4j 重建完成",
        "source_files": len(json_files),
        "processed": processed,
        "failed": failed,
        "pipeline_version": PIPELINE_VERSION,
    })


@router.get("/status/{document_id}", response_model=ApiResponse)
async def get_analyze_status(document_id: str):
    """查询分析状态"""
    status = AnalyzeStatusResponse(
        document_id=document_id,
        status="completed",
        progress=1.0,
    )
    return ApiResponse(data=status.model_dump())

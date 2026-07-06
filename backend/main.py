"""
FastAPI 应用入口（MVP模式 — 无需 Neo4j/LLM，优先读取 data/extracted/ 真源）
"""
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.config import PROJECT_NAME, VERSION
from backend.routers.mvp import router as mvp_router

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)
_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("正在启动 %s v%s (MVP模式)", PROJECT_NAME, VERSION)
    yield
    logger.info("应用已关闭")


app = FastAPI(title=PROJECT_NAME, version=VERSION, lifespan=lifespan, docs_url="/docs")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(mvp_router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("未捕获的异常: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"success": False, "error": {"code": "ERR_INTERNAL_001", "message": "服务器内部错误"}})

@app.get("/")
async def root():
    return {"project": PROJECT_NAME, "version": VERSION, "mode": "MVP", "uptime_seconds": int(time.time() - _start_time), "docs": "/docs"}

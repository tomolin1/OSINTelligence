"""
系统配置
"""

import os
from datetime import datetime

# 项目信息
PROJECT_NAME = "开源威胁情报APT研判系统"
VERSION = "1.0.0"
API_PREFIX = "/api/v1"

# 服务配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Neo4j 数据库
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# LLM API
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
LLM_MAX_CONCURRENCY = int(os.getenv("LLM_MAX_CONCURRENCY", "5"))

# 爬虫输出目录
CRAWLER_OUTPUT_DIR = os.getenv("CRAWLER_OUTPUT_DIR", "data/crawler_output")
PROCESSED_MARK_DIR = os.getenv("PROCESSED_MARK_DIR", "data/processed")

# 文件限制
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TEXT_LENGTH = 50000
MIN_TEXT_LENGTH = 10

# 图谱查询限制
MAX_GRAPH_DEPTH = 2
MAX_NODES_PER_QUERY = 100

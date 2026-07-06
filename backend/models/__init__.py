"""
Pydantic 数据模型 — 与 schema.json 契约完全对齐
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from backend.config import MIN_TEXT_LENGTH, MAX_TEXT_LENGTH


# ==================== 枚举 ====================

class SourceType(str, Enum):
    threat_report = "threat_report"
    news_article = "news_article"
    social_media = "social_media"
    forum_post = "forum_post"
    cve_database = "cve_database"
    cert_alert = "cert_alert"
    blog = "blog"
    academic_paper = "academic_paper"


class Language(str, Enum):
    zh = "zh"
    en = "en"


class EntityType(str, Enum):
    APT_GROUP = "APT_GROUP"
    MALWARE = "MALWARE"
    TOOL = "TOOL"
    CVE = "CVE"
    TECHNIQUE = "TECHNIQUE"
    PERSON = "PERSON"
    COUNTRY = "COUNTRY"
    INDUSTRY = "INDUSTRY"
    CAMPAIGN = "CAMPAIGN"
    ORGANIZATION = "ORGANIZATION"
    TIME = "TIME"


class RelationType(str, Enum):
    ATTRIBUTED_TO = "ATTRIBUTED_TO"
    USES = "USES"
    TARGETS = "TARGETS"
    DEVELOPS = "DEVELOPS"
    EXPLOITS = "EXPLOITS"
    RELATED_TO = "RELATED_TO"
    AFFILIATED_WITH = "AFFILIATED_WITH"
    LEADS_TO = "LEADS_TO"
    DISCOVERED_BY = "DISCOVERED_BY"
    EMPLOYS = "EMPLOYS"


class ThreatLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ExploitationStatus(str, Enum):
    exploited = "exploited"
    poc = "poc"
    theoretical = "theoretical"
    patched = "patched"


class CampaignStatus(str, Enum):
    ongoing = "ongoing"
    concluded = "concluded"
    attributed = "attributed"


class PersonRole(str, Enum):
    hacker = "hacker"
    commander = "commander"
    researcher = "researcher"


class ToolType(str, Enum):
    exploit_framework = "exploit_framework"
    living_off_land = "living_off_land"
    utility = "utility"


class MalwareType(str, Enum):
    trojan = "trojan"
    ransomware = "ransomware"
    backdoor = "backdoor"
    worm = "worm"


class EntityGroup(int, Enum):
    """前端颜色分组"""
    APT_GROUP = 1
    MALWARE = 2
    TOOL = 3
    CVE = 4
    TECHNIQUE = 5
    COUNTRY = 6
    INDUSTRY = 7
    PERSON = 8
    CAMPAIGN = 9
    ORGANIZATION = 10


ENTITY_TYPE_GROUP_MAP = {
    EntityType.APT_GROUP: EntityGroup.APT_GROUP,
    EntityType.MALWARE: EntityGroup.MALWARE,
    EntityType.TOOL: EntityGroup.TOOL,
    EntityType.CVE: EntityGroup.CVE,
    EntityType.TECHNIQUE: EntityGroup.TECHNIQUE,
    EntityType.COUNTRY: EntityGroup.COUNTRY,
    EntityType.INDUSTRY: EntityGroup.INDUSTRY,
    EntityType.PERSON: EntityGroup.PERSON,
    EntityType.CAMPAIGN: EntityGroup.CAMPAIGN,
    EntityType.ORGANIZATION: EntityGroup.ORGANIZATION,
    EntityType.TIME: EntityGroup.CAMPAIGN,
}


# ==================== 爬虫模块 ====================

class CrawlerMetadata(BaseModel):
    author: Optional[str] = None
    publish_date: Optional[str] = None
    tags: list[str] = []
    word_count: Optional[int] = None
    file_path: Optional[str] = None


class CrawlerOutput(BaseModel):
    """爬虫输出格式 — 对应 schema.json crawler.output_format"""
    source_url: str
    source_type: SourceType
    title: str
    raw_text: str
    language: Language
    crawl_time: datetime
    metadata: CrawlerMetadata = Field(default_factory=CrawlerMetadata)


# ==================== LLM抽取模块 ====================

class Mention(BaseModel):
    sentence: str
    offset_start: int
    offset_end: int


class Entity(BaseModel):
    """实体 — 对应 schema.json llm_extraction.entity"""
    id: str
    name: str
    type: EntityType
    aliases: list[str] = []
    description: str = ""
    source_text: str = ""
    confidence: float = Field(ge=0, le=1)
    mentions: list[Mention] = []


class Relationship(BaseModel):
    """关系 — 对应 schema.json llm_extraction.relationship"""
    id: str
    source_id: str
    target_id: str
    type: RelationType
    description: str = ""
    source_text: str = ""
    confidence: float = Field(ge=0, le=1)
    temporal: Optional[dict] = None
    mitre_attack_id: Optional[str] = None


class Summary(BaseModel):
    """文档摘要"""
    overview: str = ""
    key_findings: list[str] = []
    threat_level: ThreatLevel = ThreatLevel.MEDIUM
    relevant_ttps: list[str] = []


class LLMExtractionOutput(BaseModel):
    """LLM抽取输出 — 对应 schema.json llm_extraction.output_format"""
    document_id: str
    entities: list[Entity] = []
    relationships: list[Relationship] = []
    summary: Summary = Field(default_factory=Summary)
    analysis_time: datetime = Field(default_factory=datetime.utcnow)


# ==================== 图谱模块 ====================

class GraphNode(BaseModel):
    """图谱节点 — 对应 api_docs.md /graph 响应"""
    id: str
    name: str
    type: EntityType
    group: int
    confidence: float = 0.0
    description: str = ""
    properties: dict = {}


class GraphEdge(BaseModel):
    """图谱边 — 对应 api_docs.md /graph 响应"""
    id: str
    source: str
    target: str
    type: RelationType
    label: str = ""
    confidence: float = 0.0
    source_text: str = ""
    mitre_attack_id: Optional[str] = None


class GraphResponse(BaseModel):
    """图谱数据响应"""
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


# ==================== 请求/响应模型 ====================

class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=MIN_TEXT_LENGTH, max_length=MAX_TEXT_LENGTH)
    source_url: str
    language: Optional[Language] = None
    source_type: Optional[SourceType] = None


class AnalyzeFileResponse(BaseModel):
    document_id: str
    entities: list[Entity] = []
    relationships: list[Relationship] = []
    summary: Summary = Field(default_factory=Summary)
    analysis_time: datetime = Field(default_factory=datetime.utcnow)


class BatchAnalyzeRequest(BaseModel):
    directory: str
    resume: bool = True


class BatchAnalyzeResponse(BaseModel):
    total_files: int = 0
    processed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[dict] = []


class AnalyzeStatusResponse(BaseModel):
    document_id: str
    status: str  # pending / processing / completed / failed
    progress: float = 0.0
    entity_count: int = 0
    relationship_count: int = 0
    analysis_time_seconds: float = 0.0


class EntitySearchResult(BaseModel):
    id: str
    name: str
    type: EntityType
    aliases: list[str] = []
    description: str = ""
    confidence: float = 0.0


class EntitySearchResponse(BaseModel):
    total: int = 0
    page: int = 1
    page_size: int = 20
    items: list[EntitySearchResult] = []


class EntityDetailResponse(BaseModel):
    id: str
    name: str
    type: EntityType
    aliases: list[str] = []
    origin_country: Optional[str] = None
    active_years: Optional[str] = None
    motivation: Optional[str] = None
    description: str = ""
    first_seen: Optional[date] = None
    last_seen: Optional[date] = None
    confidence: float = 0.0
    source_count: int = 0
    related_campaigns: list[str] = []
    known_tools: list[str] = []
    target_sectors: list[str] = []


class TimelineEvent(BaseModel):
    date: str
    event: str
    type: str  # first_seen / campaign / tool_usage / last_seen


class EntityTimelineResponse(BaseModel):
    entity_id: str
    timeline: list[TimelineEvent] = []


class ReportResponse(BaseModel):
    title: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    summary: str = ""
    entity_profile: dict = {}
    timeline: list[dict] = []
    ttp_analysis: list[dict] = []
    target_analysis: list[dict] = []
    related_entities: list[dict] = []
    threat_assessment: dict = {}


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    components: dict = {}
    uptime_seconds: int = 0


# ==================== 抽取结果校验 ====================

class ValidationError_(BaseModel):
    """校验错误"""
    field: str
    message: str
    entity_id: str = ""


def validate_extraction(output: LLMExtractionOutput) -> list[ValidationError_]:
    """
    校验 LLM 抽取结果，在写入 Neo4j 之前调用。
    返回校验错误列表，空列表表示通过。
    """
    errors: list[ValidationError_] = []
    entity_ids: set[str] = set()

    for i, e in enumerate(output.entities):
        entity_ids.add(e.id)

        # 1. id 不能是占位值
        if not e.id or e.id == "ENT_UNKNOWN":
            errors.append(ValidationError_(field=f"entities[{i}].id", message="实体 ID 缺失或为占位值", entity_id=e.id))

        # 2. name 不能为空
        if not e.name or e.name.strip() == "":
            errors.append(ValidationError_(field=f"entities[{i}].name", message="实体名称不能为空", entity_id=e.id))

        # 3. type 必须是合法枚举
        if e.type not in EntityType:
            errors.append(ValidationError_(field=f"entities[{i}].type", message=f"无效实体类型: {e.type}", entity_id=e.id))

        # 4. confidence 范围
        if not (0 <= e.confidence <= 1):
            errors.append(ValidationError_(field=f"entities[{i}].confidence", message=f"置信度超出 [0,1] 范围: {e.confidence}", entity_id=e.id))

    for i, r in enumerate(output.relationships):
        # 5. source_id 必须引用已有实体
        if r.source_id not in entity_ids:
            errors.append(ValidationError_(field=f"relationships[{i}].source_id", message=f"source_id 引用了不存在的实体: {r.source_id}", entity_id=r.id))

        # 6. target_id 必须引用已有实体
        if r.target_id not in entity_ids:
            errors.append(ValidationError_(field=f"relationships[{i}].target_id", message=f"target_id 引用了不存在的实体: {r.target_id}", entity_id=r.id))

        # 7. type 必须是合法枚举
        if r.type not in RelationType:
            errors.append(ValidationError_(field=f"relationships[{i}].type", message=f"无效关系类型: {r.type}", entity_id=r.id))

        # 8. confidence 范围
        if not (0 <= r.confidence <= 1):
            errors.append(ValidationError_(field=f"relationships[{i}].confidence", message=f"置信度超出 [0,1] 范围: {r.confidence}", entity_id=r.id))

    return errors


# ==================== 统一响应 ====================

class ApiResponse(BaseModel):
    """统一成功响应"""
    success: bool = True
    data: dict | list | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ApiErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ApiErrorResponse(BaseModel):
    """统一错误响应"""
    success: bool = False
    error: ApiErrorDetail
    timestamp: datetime = Field(default_factory=datetime.utcnow)

"""
Neo4j 图数据库服务
"""

import logging
from neo4j import GraphDatabase, AsyncGraphDatabase
from backend.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)


class Neo4jService:
    def __init__(self):
        self.driver = None

    async def connect(self):
        """建立数据库连接并初始化 schema"""
        self.driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        await self.driver.verify_connectivity()
        await self._init_schema()
        logger.info("Neo4j 连接成功: %s", NEO4J_URI)

    async def _init_schema(self):
        """创建索引和约束，确保 MERGE 是 O(1)"""
        async with self.driver.session() as session:
            # Entity 标签上的 id 唯一约束（自动建索引）
            try:
                await session.run(
                    "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS "
                    "FOR (n:Entity) REQUIRE n.id IS UNIQUE"
                )
            except Exception:
                pass  # Neo4j 5.x+ 不支持 IF NOT EXISTS，忽略已存在的错误

    async def clear_all(self):
        """清空图中所有节点和关系（用于重建）"""
        async with self.driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
            logger.info("Neo4j 全量清空完成")

    async def close(self):
        """关闭连接"""
        if self.driver:
            await self.driver.close()

    # ==================== 节点操作 ====================

    async def merge_node(self, label: str, node_id: str, properties: dict):
        """创建或更新节点"""
        async with self.driver.session() as session:
            query = f"""
            MERGE (n:{label} {{id: $node_id}})
            ON CREATE SET n += $properties
            ON MATCH SET n += $properties
            RETURN n
            """
            await session.run(query, node_id=node_id, properties=properties)

    async def get_node(self, node_id: str) -> dict | None:
        """按ID获取节点"""
        async with self.driver.session() as session:
            query = "MATCH (n {id: $node_id}) RETURN n LIMIT 1"
            result = await session.run(query, node_id=node_id)
            record = await result.single()
            if record:
                node = record["n"]
                return dict(node)
            return None

    # ==================== 关系操作 ====================

    async def create_relationship(
        self, source_id: str, target_id: str,
        rel_type: str, properties: dict
    ):
        """创建关系"""
        async with self.driver.session() as session:
            query = f"""
            MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
            CREATE (a)-[r:{rel_type} $properties]->(b)
            RETURN r
            """
            await session.run(
                query,
                source_id=source_id,
                target_id=target_id,
                properties=properties
            )

    # ==================== 图谱查询 ====================

    async def get_subgraph(
        self, entity_id: str | None = None,
        depth: int = 2, types: list[str] | None = None,
        limit: int = 100
    ) -> tuple[list[dict], list[dict]]:
        """获取子图数据"""
        async with self.driver.session() as session:
            if entity_id:
                query = f"""
                MATCH path = (n)-[r*1..{depth}]-(m)
                WHERE n.id = $entity_id
                UNWIND nodes(path) AS node
                UNWIND relationships(path) AS rel
                RETURN DISTINCT node, rel
                LIMIT $limit
                """
                result = await session.run(query, entity_id=entity_id, limit=limit)
            else:
                query = """
                MATCH (n)-[r]->(m)
                RETURN n, r, m
                LIMIT $limit
                """
                result = await session.run(query, limit=limit)

            nodes_dict = {}
            edges = []

            async for record in result:
                for key in record.keys():
                    rel = record.get("rel")
                    if rel:
                        edge = {
                            "id": rel.get("id", str(rel.element_id)),
                            "source": rel.nodes[0].get("id"),
                            "target": rel.nodes[1].get("id"),
                            "type": rel.type,
                            "label": rel.get("label", rel.type),
                            "confidence": rel.get("confidence", 1.0),
                            "source_text": rel.get("source_text", ""),
                            "mitre_attack_id": rel.get("mitre_attack_id"),
                        }
                        edges.append(edge)

                        for n in rel.nodes:
                            nid = n.get("id")
                            if nid and nid not in nodes_dict:
                                node_type = list(n.labels)[0] if n.labels else "UNKNOWN"
                                nodes_dict[nid] = {
                                    "id": nid,
                                    "name": n.get("name", nid),
                                    "type": node_type,
                                    "group": self._type_to_group(node_type),
                                    "confidence": n.get("confidence", 1.0),
                                    "description": n.get("description", ""),
                                    "properties": dict(n),
                                }

            # 类型过滤
            if types:
                nodes_dict = {
                    k: v for k, v in nodes_dict.items()
                    if v["type"] in types
                }
                edges = [
                    e for e in edges
                    if e["source"] in nodes_dict and e["target"] in nodes_dict
                ]

            return list(nodes_dict.values()), edges

    async def expand_node(
        self, entity_id: str, depth: int = 1,
        relation_types: list[str] | None = None
    ) -> tuple[list[dict], list[dict]]:
        """展开节点（爆炸图）"""
        return await self.get_subgraph(entity_id, depth=depth)

    # ==================== 实体搜索 ====================

    async def search_entities(
        self, keyword: str,
        entity_type: str | None = None,
        page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        """搜索实体"""
        async with self.driver.session() as session:
            where = "n.name CONTAINS $keyword"
            params = {"keyword": keyword}

            if entity_type:
                where = f"({where} AND $entity_type IN labels(n))"
                params["entity_type"] = entity_type

            count_query = f"MATCH (n) WHERE {where} RETURN count(n) AS total"
            count_result = await session.run(count_query, **params)
            count_record = await count_result.single()
            total = count_record["total"] if count_record else 0

            skip = (page - 1) * page_size
            query = f"""
            MATCH (n) WHERE {where}
            RETURN n
            SKIP $skip LIMIT $page_size
            """
            params["skip"] = skip
            params["page_size"] = page_size
            result = await session.run(query, **params)

            items = []
            async for record in result:
                node = record["n"]
                labels = list(node.labels) if node.labels else ["UNKNOWN"]
                items.append({
                    "id": node.get("id"),
                    "name": node.get("name"),
                    "type": labels[0],
                    "aliases": node.get("aliases", []),
                    "description": node.get("description", ""),
                    "confidence": node.get("confidence", 0.0),
                })

            return items, total

    # ==================== 时间轴查询 ====================

    async def get_timeline(
        self, entity_id: str
    ) -> list[dict]:
        """获取实体时间线"""
        async with self.driver.session() as session:
            query = """
            MATCH (n {id: $entity_id})
            RETURN n.first_seen AS first_seen,
                   n.last_seen AS last_seen,
                   n.active_years AS active_years
            """
            result = await session.run(query, entity_id=entity_id)
            record = await result.single()
            events = []
            if record:
                if record.get("first_seen"):
                    events.append({
                        "date": str(record["first_seen"]),
                        "event": f"实体首次被发现",
                        "type": "first_seen"
                    })
                if record.get("last_seen"):
                    events.append({
                        "date": str(record["last_seen"]),
                        "event": "最近一次活跃记录",
                        "type": "last_seen"
                    })
            return events

    # ==================== 健康检查 ====================

    async def check_health(self) -> bool:
        """检查数据库连接状态"""
        try:
            await self.driver.verify_connectivity()
            return True
        except Exception:
            return False

    # ==================== 工具方法 ====================

    @staticmethod
    def _type_to_group(type_name: str) -> int:
        mapping = {
            "APT_GROUP": 1, "MALWARE": 2, "TOOL": 3, "CVE": 4,
            "TECHNIQUE": 5, "COUNTRY": 6, "INDUSTRY": 7,
            "PERSON": 8, "CAMPAIGN": 9, "ORGANIZATION": 10,
        }
        return mapping.get(type_name, 0)


# 全局单例
neo4j_svc = Neo4jService()

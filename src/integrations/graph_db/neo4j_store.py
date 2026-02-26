"""Neo4j graph database client for entity and relationship storage."""
from __future__ import annotations

import json
import structlog
from uuid import UUID
from neo4j import AsyncGraphDatabase, AsyncDriver
from src.models import Entity, Relationship

logger = structlog.get_logger(__name__)


class Neo4jStore:
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "password") -> None:
        self._uri = uri
        self._user = user
        self._password = password
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        self._driver = AsyncGraphDatabase.driver(self._uri, auth=(self._user, self._password))
        await self._driver.verify_connectivity()
        logger.info("neo4j_connected", uri=self._uri)

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    @property
    def driver(self) -> AsyncDriver:
        if not self._driver:
            raise RuntimeError("Neo4jStore not connected. Call connect() first.")
        return self._driver

    async def create_entity(self, entity: Entity) -> None:
        """Create or merge an entity node."""
        query = """
        MERGE (e:Entity {name: $name, entity_type: $entity_type})
        ON CREATE SET e.id = $id, e.properties = $properties, e.source_chunk_id = $source_chunk_id
        ON MATCH SET e.properties = $properties
        """
        async with self.driver.session() as session:
            await session.run(
                query,
                id=str(entity.id),
                name=entity.name,
                entity_type=entity.entity_type,
                properties=json.dumps(entity.properties),
                source_chunk_id=str(entity.source_chunk_id) if entity.source_chunk_id else None,
            )

    async def create_relationship(self, relationship: Relationship, source_name: str, target_name: str) -> None:
        """Create a relationship between two entities."""
        query = """
        MATCH (s:Entity {name: $source_name})
        MATCH (t:Entity {name: $target_name})
        MERGE (s)-[r:RELATES_TO {relationship_type: $rel_type}]->(t)
        ON CREATE SET r.id = $id, r.properties = $properties, r.source_chunk_id = $source_chunk_id
        """
        async with self.driver.session() as session:
            await session.run(
                query,
                id=str(relationship.id),
                source_name=source_name,
                target_name=target_name,
                rel_type=relationship.relationship_type,
                properties=json.dumps(relationship.properties),
                source_chunk_id=str(relationship.source_chunk_id) if relationship.source_chunk_id else None,
            )

    async def find_related_chunks(self, entity_names: list[str], max_depth: int = 2) -> list[str]:
        """Find chunk IDs related to given entities via graph traversal."""
        if not entity_names:
            return []
        query = """
        MATCH (e:Entity)
        WHERE e.name IN $names
        MATCH path = (e)-[*1..$max_depth]-(related:Entity)
        WHERE related.source_chunk_id IS NOT NULL
        RETURN DISTINCT related.source_chunk_id AS chunk_id
        """
        chunk_ids: list[str] = []
        async with self.driver.session() as session:
            result = await session.run(query, names=entity_names, max_depth=max_depth)
            records = await result.data()
            for record in records:
                if record.get("chunk_id"):
                    chunk_ids.append(record["chunk_id"])
        return chunk_ids

    async def extract_entities_from_text(self, text: str, llm_provider: object) -> tuple[list[Entity], list[tuple[Entity, Entity, Relationship]]]:
        """Use LLM to extract entities and relationships from text.

        The llm_provider should have a generate() method (LLMProvider protocol).
        Returns (entities, [(source_entity, target_entity, relationship), ...])
        """
        prompt = f"""Extract named entities and their relationships from the following text.
Return a JSON object with:
- "entities": [{{"name": "...", "type": "..."}}]
- "relationships": [{{"source": "...", "target": "...", "type": "..."}}]

Text:
{text}

Return ONLY valid JSON, no other text."""

        response = await llm_provider.generate(prompt)  # type: ignore[union-attr]

        try:
            # Try to parse the JSON from the response
            # Handle potential markdown code blocks
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]

            data = json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            logger.warning("entity_extraction_failed", response_preview=response[:200])
            return [], []

        entities: list[Entity] = []
        entity_map: dict[str, Entity] = {}

        for ent_data in data.get("entities", []):
            entity = Entity(name=ent_data["name"], entity_type=ent_data.get("type", "unknown"))
            entities.append(entity)
            entity_map[entity.name] = entity

        triples: list[tuple[Entity, Entity, Relationship]] = []
        for rel_data in data.get("relationships", []):
            source = entity_map.get(rel_data.get("source", ""))
            target = entity_map.get(rel_data.get("target", ""))
            if source and target:
                rel = Relationship(
                    source_entity_id=source.id,
                    target_entity_id=target.id,
                    relationship_type=rel_data.get("type", "related_to"),
                )
                triples.append((source, target, rel))

        return entities, triples

    async def clear(self) -> None:
        """Delete all nodes and relationships. Use with caution."""
        async with self.driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        logger.info("neo4j_cleared")

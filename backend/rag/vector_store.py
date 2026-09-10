from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from typing import List, Dict, Any, Optional
from rag.embeddings import embedding_engine
import uuid
import os


class ThreatVectorStore:
    def __init__(self):
        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", 6333))
        self.client = QdrantClient(host=host, port=port)
        self._ensure_collections()

    def _ensure_collections(self):
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if "threat_patterns" not in collection_names:
            self.client.create_collection(
                collection_name="threat_patterns",
                vectors_config=VectorParams(
                    size=384,
                    distance=Distance.COSINE
                )
            )

        if "compliance_frameworks" not in collection_names:
            self.client.create_collection(
                collection_name="compliance_frameworks",
                vectors_config=VectorParams(
                    size=384,
                    distance=Distance.COSINE
                )
            )

    async def add_threat_pattern(self, pattern: Dict[str, Any]):
        embedding = embedding_engine.embed(pattern["text"])
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "text": pattern["text"],
                "threat_type": pattern["threat_type"],
                "source": pattern.get("source", "unknown"),
                "severity": pattern.get("severity", "medium")
            }
        )
        self.client.upsert(
            collection_name="threat_patterns",
            points=[point]
        )

    async def query(self, text: str, collection: str = "threat_patterns",
                    top_k: int = 5) -> Dict[str, Any]:
        embedding = embedding_engine.embed(text)
        results = self.client.search(
            collection_name=collection,
            query_vector=embedding,
            limit=top_k
        )

        return {
            "chunks": [
                {
                    "id": r.id,
                    "text": r.payload.get("text", ""),
                    "score": r.score,
                    "metadata": {k: v for k, v in r.payload.items() if k != "text"}
                }
                for r in results
            ],
            "chunk_ids": [r.id for r in results],
            "similarities": [r.score for r in results]
        }

    async def add_compliance_rule(self, rule: Dict[str, Any]):
        embedding = embedding_engine.embed(rule["text"])
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "text": rule["text"],
                "framework": rule["framework"],
                "control_id": rule["control_id"],
                "description": rule.get("description", "")
            }
        )
        self.client.upsert(
            collection_name="compliance_frameworks",
            points=[point]
        )

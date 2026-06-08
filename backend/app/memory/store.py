"""
J.A.Y. Vector Memory Store — ChromaDB + semantic search
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Optional, Dict, Any
import logging
import os
import uuid
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    Persistent vector memory with semantic search.
    Stores: facts, preferences, conversations, lessons, research, projects.
    """

    def __init__(self):
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.encoder = None  # Lazy load
        self._collections: Dict[str, chromadb.Collection] = {}

    def _get_encoder(self) -> SentenceTransformer:
        if self.encoder is None:
            logger.info("Loading sentence transformer model...")
            self.encoder = SentenceTransformer(settings.EMBEDDING_MODEL)
        return self.encoder

    def _get_collection(self, namespace: str = "general") -> chromadb.Collection:
        if namespace not in self._collections:
            self._collections[namespace] = self.client.get_or_create_collection(
                name=f"jay_{namespace}",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[namespace]

    def _embed(self, text: str) -> List[float]:
        encoder = self._get_encoder()
        return encoder.encode(text, normalize_embeddings=True).tolist()

    async def store(
        self,
        content: str,
        category: str = "general",
        metadata: Optional[Dict] = None,
        namespace: str = "general",
        doc_id: Optional[str] = None,
    ) -> str:
        """Store a memory entry with embedding."""
        collection = self._get_collection(namespace)
        entry_id = doc_id or str(uuid.uuid4())
        embedding = self._embed(content)

        meta = {
            "category": category,
            "timestamp": datetime.utcnow().isoformat(),
            "namespace": namespace,
        }
        if metadata:
            # ChromaDB only supports string/int/float/bool values
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    meta[k] = v
                else:
                    meta[k] = str(v)

        collection.upsert(
            ids=[entry_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[meta],
        )
        logger.debug(f"Stored memory [{entry_id}] in {namespace}/{category}")
        return entry_id

    async def search(
        self,
        query: str,
        namespace: str = "general",
        category: Optional[str] = None,
        n_results: int = 10,
        min_score: float = 0.0,
    ) -> List[Dict]:
        """Semantic search over memory."""
        collection = self._get_collection(namespace)
        embedding = self._embed(query)

        where = {}
        if category:
            where["category"] = {"$eq": category}

        results = collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, collection.count() or 1),
            where=where if where else None,
            include=["documents", "metadatas", "distances"],
        )

        memories = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 1.0
                score = 1.0 - distance  # cosine distance → similarity
                if score >= min_score:
                    memories.append({
                        "id": doc_id,
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "score": round(score, 4),
                    })

        memories.sort(key=lambda x: x["score"], reverse=True)
        return memories

    async def delete(self, doc_id: str, namespace: str = "general"):
        """Delete a memory entry."""
        collection = self._get_collection(namespace)
        collection.delete(ids=[doc_id])

    async def get_all(self, namespace: str = "general", category: Optional[str] = None) -> List[Dict]:
        """Retrieve all memories from a namespace."""
        collection = self._get_collection(namespace)
        where = {"category": {"$eq": category}} if category else None
        results = collection.get(where=where, include=["documents", "metadatas"])

        memories = []
        if results["ids"]:
            for i, doc_id in enumerate(results["ids"]):
                memories.append({
                    "id": doc_id,
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                })
        return memories

    async def count(self, namespace: str = "general") -> int:
        collection = self._get_collection(namespace)
        return collection.count()


# Global memory store
memory_store = MemoryStore()

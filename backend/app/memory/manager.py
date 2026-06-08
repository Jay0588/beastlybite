"""
J.A.Y. Memory Manager — High-level memory operations
Handles extraction, storage, retrieval, and context building
"""
from typing import List, Optional, Dict, Any
import logging
import re
from datetime import datetime
from app.memory.store import memory_store
from app.core.config import settings

logger = logging.getLogger(__name__)

MEMORY_EXTRACTION_PROMPT = """Analyze this conversation and extract important facts, preferences, habits, and information about the user that should be remembered for future conversations.

Extract ONLY genuinely important information. Format as JSON array:
[
  {"content": "User's fact/preference", "category": "preference|fact|habit|project|lesson|contact|task", "importance": 0.0-1.0}
]

If nothing important to remember, return: []

Conversation:
{conversation}
"""


class MemoryManager:
    """
    High-level memory management for J.A.Y.
    - Automatic extraction from conversations
    - Context building for prompts
    - Profile management
    """

    NAMESPACES = {
        "general": "General facts and preferences",
        "conversations": "Conversation history",
        "projects": "Project-specific knowledge",
        "trading": "Trading knowledge and strategies",
        "research": "Research findings",
        "code": "Code patterns and solutions",
    }

    async def remember(
        self,
        content: str,
        category: str = "fact",
        namespace: str = "general",
        importance: float = 0.5,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Store a memory explicitly."""
        meta = {"importance": importance, "category": category}
        if metadata:
            meta.update(metadata)
        doc_id = await memory_store.store(
            content=content,
            category=category,
            namespace=namespace,
            metadata=meta,
        )
        logger.info(f"Remembered: [{category}] {content[:80]}...")
        return doc_id

    async def recall(
        self,
        query: str,
        namespace: str = "general",
        category: Optional[str] = None,
        n: int = 5,
    ) -> List[Dict]:
        """Search memories semantically."""
        results = await memory_store.search(
            query=query,
            namespace=namespace,
            category=category,
            n_results=n,
            min_score=settings.MEMORY_SIMILARITY_THRESHOLD,
        )
        # Update access tracking
        for r in results:
            await memory_store.store(
                content=r["content"],
                category=r["metadata"].get("category", "general"),
                namespace=namespace,
                metadata={**r["metadata"], "access_count": r["metadata"].get("access_count", 0) + 1,
                           "last_accessed": datetime.utcnow().isoformat()},
                doc_id=r["id"],
            )
        return results

    async def build_context(self, query: str, max_items: int = 6) -> str:
        """Build memory context string for AI prompts."""
        # Search across namespaces
        results = []
        for ns in ["general", "projects", "research"]:
            found = await memory_store.search(
                query=query,
                namespace=ns,
                n_results=3,
                min_score=0.65,
            )
            results.extend(found)

        if not results:
            return ""

        # Sort by score, deduplicate
        results.sort(key=lambda x: x["score"], reverse=True)
        seen = set()
        unique = []
        for r in results:
            if r["content"] not in seen:
                seen.add(r["content"])
                unique.append(r)
            if len(unique) >= max_items:
                break

        context_lines = ["[RELEVANT MEMORIES]"]
        for r in unique:
            cat = r["metadata"].get("category", "fact")
            context_lines.append(f"• [{cat}] {r['content']}")
        context_lines.append("[/RELEVANT MEMORIES]")
        return "\n".join(context_lines)

    async def extract_and_store_from_conversation(
        self,
        messages: List[Dict],
        provider_manager=None,
    ) -> List[str]:
        """Automatically extract important facts from a conversation and store them."""
        if not provider_manager:
            return []
        try:
            from app.providers.base import CompletionRequest, ChatMessage, MessageRole
            import json

            conversation_text = "\n".join(
                [f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in messages[-10:]]
            )
            request = CompletionRequest(
                messages=[ChatMessage(role=MessageRole.USER, content=conversation_text)],
                system_prompt=MEMORY_EXTRACTION_PROMPT.replace("{conversation}", conversation_text),
                temperature=0.1,
                max_tokens=1000,
            )
            response = await provider_manager.complete(request)
            content = response.content.strip()

            # Extract JSON
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if not json_match:
                return []

            items = json.loads(json_match.group())
            stored_ids = []
            for item in items:
                if isinstance(item, dict) and item.get("content"):
                    doc_id = await self.remember(
                        content=item["content"],
                        category=item.get("category", "fact"),
                        importance=float(item.get("importance", 0.5)),
                    )
                    stored_ids.append(doc_id)
            return stored_ids
        except Exception as e:
            logger.error(f"Memory extraction failed: {e}")
            return []

    async def get_user_profile(self) -> Dict[str, str]:
        """Get all known user preferences and facts."""
        memories = await memory_store.get_all(namespace="general", category="preference")
        profile = {}
        for m in memories:
            profile[m["id"]] = m["content"]
        return profile

    async def search_all_namespaces(self, query: str, n: int = 10) -> List[Dict]:
        """Search across all memory namespaces."""
        all_results = []
        for ns in self.NAMESPACES:
            found = await memory_store.search(query=query, namespace=ns, n_results=3, min_score=0.5)
            for r in found:
                r["namespace"] = ns
            all_results.extend(found)
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:n]


memory_manager = MemoryManager()

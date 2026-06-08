"""
J.A.Y. Web Tools — Search, browse, fetch content
"""
import httpx
import logging
from typing import Dict, Any, List, Optional
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web using DuckDuckGo"

    async def execute(self, params: Dict[str, Any]) -> Dict:
        query = params.get("query", "")
        max_results = params.get("max_results", 5)

        if not query:
            return {"success": False, "error": "No query provided"}

        try:
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", ""),
                    })

            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(
                    f"{i}. **{r['title']}**\n{r['snippet']}\nURL: {r['url']}"
                )

            return {
                "success": True,
                "output": "\n\n".join(formatted),
                "results": results,
                "count": len(results),
            }
        except Exception as e:
            # Fallback to basic HTTP search
            logger.warning(f"DuckDuckGo search failed: {e}")
            return {"success": False, "error": str(e), "output": "Search unavailable"}


class FetchURLTool(BaseTool):
    name = "fetch_url"
    description = "Fetch and extract text content from a URL"

    async def execute(self, params: Dict[str, Any]) -> Dict:
        url = params.get("url", "")
        if not url:
            return {"success": False, "error": "No URL provided"}

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=15.0,
                headers={"User-Agent": "Mozilla/5.0 J.A.Y. Research Agent"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")

                if "html" in content_type:
                    # Use trafilatura for clean text extraction
                    try:
                        import trafilatura
                        text = trafilatura.extract(response.text, include_links=False)
                        if not text:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(response.text, "html.parser")
                            text = soup.get_text(separator="\n", strip=True)
                    except Exception:
                        text = response.text[:5000]
                else:
                    text = response.text

                # Limit
                if len(text) > 20000:
                    text = text[:20000] + "\n[...content truncated]"

                return {
                    "success": True,
                    "output": text,
                    "url": url,
                    "status_code": response.status_code,
                    "content_type": content_type,
                }
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}


class NewsFeedTool(BaseTool):
    name = "get_news"
    description = "Get latest news for a topic or symbol"

    async def execute(self, params: Dict[str, Any]) -> Dict:
        topic = params.get("topic", "")
        symbol = params.get("symbol", "")
        search_term = symbol or topic

        if not search_term:
            return {"success": False, "error": "No topic or symbol provided"}

        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.news(search_term, max_results=8))

            formatted = []
            for r in results:
                formatted.append(
                    f"**{r.get('title', '')}**\n"
                    f"{r.get('body', '')}\n"
                    f"Source: {r.get('source', '')} | {r.get('date', '')}\n"
                    f"URL: {r.get('url', '')}"
                )

            return {
                "success": True,
                "output": "\n\n".join(formatted),
                "articles": results,
                "count": len(results),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

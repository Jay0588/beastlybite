"""
J.A.Y. Creative Agent — Image generation, UI concepts, marketing materials
"""
from typing import List, Dict, Optional
import logging
from app.agents.base import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)

CREATIVE_SYSTEM = """You are J.A.Y.'s Creative Agent — expert in design, visual concepts, and creative work.

Capabilities:
- Generate detailed image prompts (for DALL-E, Midjourney, Stable Diffusion)
- Design UI/UX concepts
- Create marketing copy
- Generate social media content
- Design logo concepts
- Create presentation structures

For image generation: provide:
1. Optimized prompt for the requested model
2. Negative prompt (what to avoid)
3. Style suggestions
4. Size recommendations

For UI/UX: provide:
1. Layout description
2. Color palette
3. Typography suggestions
4. Component breakdown
5. Interaction patterns

For marketing:
1. Headlines
2. Body copy
3. CTA suggestions
4. Platform-specific adaptations"""


class CreativeAgent(BaseAgent):
    name = "creative"
    description = "Generate images, UI concepts, marketing materials, creative content"
    capabilities = ["image_generation", "ui_design", "marketing", "social_media", "logo"]

    async def run(self, context: AgentContext) -> AgentResult:
        self._messages = []
        self._emit(f"Creative task: {context.user_query[:100]}", "thought")

        task_type = self._detect_creative_type(context.user_query)
        self._emit(f"Creative type: {task_type}", "thought")

        messages = [{"role": "user", "content": context.user_query}]

        try:
            # Try image generation if it's an image task
            if task_type == "image":
                output = await self._handle_image_generation(context.user_query, messages)
            else:
                output = await self._llm(messages, system=CREATIVE_SYSTEM, temperature=0.8)

            self._emit("Creative work complete", "result")
            return AgentResult(
                agent=self.name,
                success=True,
                output=output,
                messages=self._messages,
            )
        except Exception as e:
            logger.error(f"Creative agent error: {e}")
            return AgentResult(agent=self.name, success=False, output=str(e), error=str(e))

    def _detect_creative_type(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["generate image", "create image", "image of", "picture", "photo", "logo", "thumbnail", "banner", "illustration"]):
            return "image"
        elif any(w in q for w in ["ui", "interface", "design", "wireframe", "mockup", "layout"]):
            return "ui"
        elif any(w in q for w in ["marketing", "ad", "advertisement", "social media", "post", "caption"]):
            return "marketing"
        elif any(w in q for w in ["video", "animation", "motion"]):
            return "video"
        return "general"

    async def _handle_image_generation(self, query: str, messages: List[Dict]) -> str:
        """Handle image generation — tries OpenAI DALL-E, falls back to prompt generation."""
        if self.provider_manager:
            try:
                from openai import AsyncOpenAI
                from app.core.config import settings
                if settings.OPENAI_API_KEY:
                    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                    response = await client.images.generate(
                        model="dall-e-3",
                        prompt=query,
                        n=1,
                        size="1024x1024",
                        quality="standard",
                    )
                    url = response.data[0].url
                    revised = response.data[0].revised_prompt
                    return f"**Image Generated**\n\nURL: {url}\n\nRevised prompt: {revised}"
            except Exception as e:
                logger.warning(f"DALL-E failed: {e}, falling back to prompt generation")

        # Fallback: Generate an optimized prompt
        prompt_request = f"""Create an optimized image generation prompt for: {query}

Provide:
1. **Main Prompt** (detailed, for DALL-E 3 or Midjourney)
2. **Negative Prompt** (what to avoid)
3. **Style Tags**
4. **Aspect Ratio** recommendation
5. **Alternative Prompt** (different style)"""
        messages[0]["content"] = prompt_request
        return await self._llm(messages, system=CREATIVE_SYSTEM, temperature=0.7)

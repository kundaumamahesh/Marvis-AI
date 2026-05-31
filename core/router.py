import json
import re

from ai.llm_client import LLMClient


class Router:

    llm = LLMClient()

    VALID_TASKS = [
        "chat",
        "powerpoint",
        "word",
        "excel",
        "image",
        "video",
        "open_app",
        "close_app",
        "volume_control",
        "web_search",
        "developer"
    ]

    @staticmethod
    def _default_response():
        return {
            "task": "chat",
            "confidence": 0.50,
            "features": {}
        }

    @staticmethod
    def _contains_any(text, keywords):
        return any(keyword in text for keyword in keywords)

    @staticmethod
    async def detect(text: str):

        text = text.strip()

        if not text:
            return Router._default_response()

        lower = text.lower()
        words = lower.split()

        # ==================================================
        # 🚀 HARD MANUAL ROUTING (FAST + RELIABLE)
        # ==================================================

        # -------------------------
        # OPEN APP
        # -------------------------
        if words and words[0] in [
            "open",
            "launch",
            "run",
            "start"
        ]:

            target = " ".join(words[1:]).strip()

            blocked_targets = [
                "project",
                "website",
                "app",
                "clone",
                "system",
                "api",
                "frontend",
                "backend"
            ]

            if not any(
                blocked in target
                for blocked in blocked_targets
            ):
                return {
                    "task": "open_app",
                    "confidence": 1.0,
                    "features": {
                        "target": target
                    }
                }

        # -------------------------
        # CLOSE APP
        # -------------------------
        if (
            words
            and words[0] in
            ["close", "kill", "stop", "exit"]
            and len(words) > 1
        ):

            if (
                "audio" not in words
                and "listening" not in words
            ):

                target = " ".join(words[1:])

                return {
                    "task": "close_app",
                    "confidence": 1.0,
                    "features": {
                        "target": target
                    }
                }

        # ==================================================
        # 💻 DEVELOPER MODE
        # ==================================================

        developer_keywords = [

            # General coding
            "build",
            "develop",
            "code",
            "program",
            "software",
            "project",
            "application",

            # App requests
            "create app",
            "make app",
            "web app",
            "mobile app",
            "desktop app",

            # Websites
            "website",
            "landing page",
            "dashboard",
            "admin panel",

            # Frontend
            "frontend",
            "html",
            "css",
            "javascript",
            "typescript",
            "react",
            "reactjs",
            "nextjs",
            "vue",
            "angular",
            "tailwind",

            # Backend
            "backend",
            "api",
            "rest api",
            "server",
            "microservice",
            "fastapi",
            "flask",
            "django",
            "node",
            "nodejs",
            "express",

            # Desktop
            "pyqt",
            "pyqt6",
            "electron",
            "tkinter",
            "javafx",

            # Mobile
            "flutter",
            "react native",
            "kotlin",
            "swift",

            # Databases
            "database",
            "postgresql",
            "mysql",
            "mongodb",
            "sqlite",
            "redis",
            "sql",

            # DevOps
            "docker",
            "kubernetes",
            "nginx",
            "ci/cd",

            # AI / ML
            "rag",
            "langchain",
            "pytorch",
            "tensorflow",
            "chatbot",
            "agent",

            # Popular clones
            "clone",
            "netflix clone",
            "youtube clone",
            "spotify clone",
            "amazon clone",
            "instagram clone",
            "whatsapp clone",

            # Common systems
            "hospital management system",
            "ecommerce",
            "crm",
            "erp",
            "attendance system",
            "management system"
        ]

        developer_phrases = [
            "build me",
            "build a",
            "build an",
            "make a",
            "make an",
            "create a",
            "create an",
            "write code",
            "generate code",
            "full stack",
            "production ready"
        ]

        office_keywords = [
            "powerpoint",
            "ppt",
            "slides",
            "presentation",
            "word document",
            "docx",
            "essay",
            "report",
            "excel",
            "spreadsheet"
        ]

        media_keywords = [
            "generate image",
            "create image",
            "make image",
            "generate video",
            "create video",
            "make video"
        ]

        is_developer_request = (
            Router._contains_any(
                lower,
                developer_keywords
            )
            or Router._contains_any(
                lower,
                developer_phrases
            )
        )

        # Prevent false detection
        if (
            is_developer_request
            and not Router._contains_any(
                lower,
                office_keywords
            )
            and not Router._contains_any(
                lower,
                media_keywords
            )
        ):

            return {
                "task": "developer",
                "confidence": 1.0,
                "features": {
                    "developer_mode": True,
                    "request": text,
                    "production_mode": True,
                    "full_stack": True,
                    "auto_continue": True
                }
            }

        # -------------------------
        # POWERPOINT
        # -------------------------
        ppt_words = [
            "powerpoint",
            "presentation",
            "slides",
            "slide deck",
            "ppt"
        ]

        if Router._contains_any(
            lower,
            ppt_words
        ):

            return {
                "task": "powerpoint",
                "confidence": 1.0,
                "features": {
                    "images": True
                }
            }

        # -------------------------
        # WORD DOCUMENT
        # -------------------------
        word_keywords = [
            "word document",
            "docx",
            "essay",
            "document",
            "report",
            "letter",
            "resume"
        ]

        if Router._contains_any(
            lower,
            word_keywords
        ):

            return {
                "task": "word",
                "confidence": 1.0,
                "features": {}
            }

        # -------------------------
        # EXCEL
        # -------------------------
        excel_keywords = [
            "excel",
            "spreadsheet",
            "xlsx",
            "table",
            "budget",
            "sheet"
        ]

        if Router._contains_any(
            lower,
            excel_keywords
        ):

            return {
                "task": "excel",
                "confidence": 1.0,
                "features": {}
            }

        # -------------------------
        # IMAGE GENERATION
        # -------------------------
        image_keywords = [
            "generate image",
            "create image",
            "make image",
            "draw",
            "art",
            "picture",
            "photo",
            "poster",
            "logo",
            "lovely image"
        ]

        if Router._contains_any(
            lower,
            image_keywords
        ):

            return {
                "task": "image",
                "confidence": 1.0,
                "features": {}
            }

        # -------------------------
        # VIDEO GENERATION
        # -------------------------
        video_keywords = [
            "generate video",
            "create video",
            "make video",
            "animation",
            "movie",
            "clip"
        ]

        if Router._contains_any(
            lower,
            video_keywords
        ):

            return {
                "task": "video",
                "confidence": 1.0,
                "features": {}
            }

        # -------------------------
        # WEATHER / WEB SEARCH
        # -------------------------
        weather_words = [
            "weather",
            "temperature",
            "forecast",
            "rain",
            "humidity",
            "climate"
        ]

        realtime_words = [
            "today",
            "now",
            "current",
            "latest",
            "live",
            "right now",
            "tomorrow",
            "yesterday"
        ]

        search_words = [
            "who is",
            "what is",
            "when is",
            "latest",
            "news",
            "price",
            "stock",
            "score",
            "won",
            "update"
        ]

        if Router._contains_any(
            lower,
            weather_words
        ):

            return {
                "task": "web_search",
                "confidence": 1.0,
                "features": {
                    "query": text
                }
            }

        if Router._contains_any(
            lower,
            realtime_words
        ):

            return {
                "task": "web_search",
                "confidence": 0.95,
                "features": {
                    "query": text
                }
            }

        if Router._contains_any(
            lower,
            search_words
        ):

            return {
                "task": "web_search",
                "confidence": 0.90,
                "features": {
                    "query": text
                }
            }

        # -------------------------
        # VOLUME CONTROL
        # -------------------------
        volume_words = [
            "volume",
            "mute",
            "unmute",
            "speaker",
            "sound"
        ]

        if Router._contains_any(
            lower,
            volume_words
        ):

            level = 50

            numbers = re.findall(
                r"\d+",
                lower
            )

            if numbers:
                level = max(
                    0,
                    min(
                        100,
                        int(numbers[0])
                    )
                )

            return {
                "task": "volume_control",
                "confidence": 1.0,
                "features": {
                    "level": level
                }
            }

        # ==================================================
        # FALLBACK TO LLM
        # ==================================================

        routing_prompt = f"""
You are the routing brain of MARVIS AI.

Choose EXACTLY one task.

Available tasks:
chat
open_app
close_app
volume_control
web_search
powerpoint
word
excel
image
video
developer

Rules:
- Coding/software request = developer
- Websites/apps/APIs = developer
- PowerPoint/PPT/slides = powerpoint
- Word/report/docx = word
- Excel/sheet/table = excel
- Image/art/logo/poster = image
- Video/animation/movie = video
- Weather/latest/news = web_search

Return ONLY valid JSON.

Format:
{{
    "task": "chat",
    "confidence": 0.90,
    "features": {{}}
}}

User Request:
{text}
"""

        try:

            response = await Router.llm.generate(
                routing_prompt,
                text
            )

            print(
                f"[ROUTER RAW]: "
                f"{response}"
            )

            match = re.search(
                r"\{.*\}",
                response,
                re.DOTALL
            )

            if not match:
                return Router._default_response()

            data = json.loads(
                match.group()
            )

            task = data.get(
                "task",
                "chat"
            )

            if task not in Router.VALID_TASKS:
                return Router._default_response()

            return {
                "task": task,
                "confidence": float(
                    data.get(
                        "confidence",
                        0.80
                    )
                ),
                "features": data.get(
                    "features",
                    {}
                )
            }

        except Exception as e:

            print(
                f"[ROUTER ERROR]: "
                f"{str(e)}"
            )

            return Router._default_response()
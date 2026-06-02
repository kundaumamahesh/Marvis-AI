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

    # ── Fast keyword pre-check (fires before the LLM round-trip) ────────────
    _WEB_SEARCH_KEYWORDS = [
        # Weather
        "weather", "temperature", "forecast", "humidity", "rain today",
        # News & current events
        "news", "latest", "today", "current", "live", "right now", "update",
        "breaking", "recently", "just happened",
        # Finance
        "stock", "price of", "bitcoin", "crypto", "market", "nasdaq",
        "nifty", "sensex", "usd", "inr", "exchange rate",
        # Sports
        "score", "match result", "ipl", "cricket", "football", "nba",
        # General live lookups
        "who is the president", "who won", "population of",
        "how many covid", "earthquake", "hurricane",
    ]

    @staticmethod
    def _quick_web_check(text: str):
        """Returns a web_search result dict if the query is obviously live-data, else None."""
        lower = text.lower()
        for kw in Router._WEB_SEARCH_KEYWORDS:
            if kw in lower:
                return {
                    "task": "web_search",
                    "confidence": 0.92,
                    "features": {"query": text.strip()}
                }
        return None

    @staticmethod
    async def detect(text: str):
        text = text.strip()
        if not text:
            return Router._default_response()

        # Fast-path: skip the LLM call for obvious live-data queries
        quick = Router._quick_web_check(text)
        if quick:
            return quick

        routing_prompt = """You are the routing brain of MARVIS AI, a state-of-the-art intelligent routing agent.

Your job is to analyze the User Request and classify it into EXACTLY ONE of the following tasks based on the intent:

1. "developer":
   - Intent: Writing code, programming, writing scripts, building websites, web apps, backend/frontend development, APIs, servers, databases, mobile apps, desktop apps, or general software engineering tasks in any programming language (Python, Javascript, TypeScript, Rust, Go, C++, C#, HTML/CSS, Java, etc.).
   - Examples: "build a react app", "write a python script to download files", "create a website", "how to write a server in rust".

2. "open_app":
   - Intent: Launching or opening a local computer application (e.g. notepad, chrome, calculator, cmd, terminal, excel, paint, etc.).
   - Examples: "open notepad", "launch chrome", "start calculator".
   - You MUST extract the application name and place it in the "features" object under the "target" key. E.g. {"target": "notepad"}

3. "close_app":
   - Intent: Terminating, closing, or killing a running computer application.
   - Examples: "close notepad", "kill chrome", "exit paint".
   - You MUST extract the application name and place it in the "features" object under the "target" key. E.g. {"target": "notepad"}

4. "volume_control":
   - Intent: Adjusting, muting, or unmuting the system volume.
   - Examples: "increase volume to 80", "mute sound", "set volume to 20%".
   - You MUST extract the volume percentage as an integer (0-100) and place it in the "features" object under the "level" key. E.g. {"level": 80}

5. "web_search":
   - Intent: ANY query that requires live, real-time, or up-to-date information from the internet:
     weather, current temperature, latest news, live sports scores, stock/crypto prices,
     recent events, current office-holders, product prices, current exchange rates, today's
     headlines, or anything where the answer could have changed in the last 24 hours.
   - Examples: "what is the weather today", "latest news on AI", "bitcoin price", "who won IPL 2025",
     "current USD to INR rate", "earthquake news", "Mangalagiri weather".
   - You MUST extract or clean the search query and place it in the "features" object under the "query" key.
     E.g. {"query": "weather Mangalagiri"}

6. "powerpoint":
   - Intent: Specifically creating, generating, or designing a PowerPoint presentation, slide deck, or ppt file.
   - Examples: "create a presentation on history", "generate 5 slides about space".

7. "word":
   - Intent: Specifically creating, writing, or generating a Word document, docx report, essay, letter, or resume document.
   - Examples: "write a report on sales", "create a word document essay about AI".

8. "excel":
   - Intent: Specifically creating, formatting, or generating an Excel spreadsheet, budget sheet, table, csv, or xlsx workbook.
   - Examples: "create an excel sheet of monthly budget", "generate a table of grades".

9. "image":
   - Intent: Generating or drawing an image, artwork, illustration, painting, logo, or picture.
   - Examples: "generate an image of a red cat", "draw a futuristic city picture".

10. "video":
    - Intent: Generating a video, clip, movie, or animation.
    - Examples: "create a video about space travel", "generate a short animation clip".

11. "chat":
    - Intent: General conversation, chit-chat, greetings, questions that don't fit any other category,
      general explanations, math, system questions, or basic advice.
    - Examples: "hello", "how are you", "explain quantum computing", "solve 2+2".

CRITICAL INSTRUCTIONS:
- You must return ONLY a valid JSON object. Do not wrap the JSON in markdown blocks like ```json ... ```, and do not output any other conversational text or explanations.
- Output JSON in this exact format:
{
    "task": "<selected_task>",
    "confidence": <float_between_0.0_and_1.0>,
    "features": { ... }
}"""

        try:
            response = await Router.llm.generate(
                routing_prompt,
                f"User Request: {text}",
                use_history=False,
                save_to_memory=False
            )

            print(f"[ROUTER RAW]: {response}")

            match = re.search(r"\{.*\}", response, re.DOTALL)
            if not match:
                return Router._default_response()

            data = json.loads(match.group())
            task = data.get("task", "chat")

            if task not in Router.VALID_TASKS:
                return Router._default_response()

            return {
                "task": task,
                "confidence": float(data.get("confidence", 0.80)),
                "features": data.get("features", {})
            }

        except Exception as e:
            print(f"[ROUTER ERROR]: {str(e)}")
            return Router._default_response()
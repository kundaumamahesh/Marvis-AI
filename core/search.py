import asyncio
import urllib.request
import urllib.parse
import json
import re


class WebSearchEngine:

    # ──────────────────────────────────────────────────────────────────────────
    # WEATHER  (wttr.in — free, never blocks Python IPs)
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _extract_city(query: str) -> str:
        """
        Pulls the most likely city name out of a weather query.
        Falls back to Vijayawada (your default location) if nothing found.
        """
        query_lower = query.lower()

        # Strip common filler phrases so only the location remains
        fillers = [
            "weather in", "weather at", "weather for", "weather of",
            "what is the weather", "what's the weather", "whats the weather",
            "current weather", "today's weather", "todays weather",
            "temperature in", "temperature at", "climate in",
            "weather", "temperature", "forecast", "today", "now",
            "current", "what is", "what's", "how is", "how's", "the"
        ]
        cleaned = query_lower
        for filler in sorted(fillers, key=len, reverse=True):
            cleaned = cleaned.replace(filler, " ")

        city = " ".join(cleaned.split()).strip().title()

        # Reject garbage short tokens and fall back to default
        if not city or len(city) < 2 or city.lower() in ("in", "at", "of", "a", "?"):
            city = "Vijayawada"

        return city

    @staticmethod
    def _fetch_weather(query: str) -> str:
        city = WebSearchEngine._extract_city(query)
        try:
            url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode())

            cur = data["current_condition"][0]
            area = data.get("nearest_area", [{}])[0]
            area_name = area.get("areaName", [{}])[0].get("value", city)

            temp_c   = cur["temp_C"]
            temp_f   = cur["temp_F"]
            feels    = cur["FeelsLikeC"]
            desc     = cur["weatherDesc"][0]["value"]
            humidity = cur["humidity"]
            wind_kph = cur["windspeedKmph"]
            uv       = cur.get("uvIndex", "N/A")
            vis      = cur.get("visibility", "N/A")

            # Today's forecast
            today = data.get("weather", [{}])[0]
            max_c = today.get("maxtempC", "?")
            min_c = today.get("mintempC", "?")

            return (
                f"[Weather] Real-time report for {area_name}\n"
                f"URL: https://wttr.in/{urllib.parse.quote(city)}\n"
                f"Context: Temperature {temp_c}°C ({temp_f}°F), feels like {feels}°C. "
                f"Condition: {desc}. Today High/Low: {max_c}°C / {min_c}°C. "
                f"Humidity: {humidity}%. Wind: {wind_kph} km/h. "
                f"UV Index: {uv}. Visibility: {vis} km."
            )
        except Exception as e:
            return f"[Weather] Could not retrieve weather for '{city}': {e}"

    # ──────────────────────────────────────────────────────────────────────────
    # DUCKDUCKGO INSTANT ANSWER  (zero-scraping, official API endpoint)
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _fetch_ddg_instant(query: str) -> str:
        """
        Calls DuckDuckGo's free Instant Answer JSON API.
        Returns a short abstract if one exists, empty string otherwise.
        """
        try:
            url = (
                "https://api.duckduckgo.com/?q="
                + urllib.parse.quote(query)
                + "&format=json&no_html=1&skip_disambig=1"
            )
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MARVIS-AI-Bot/2.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode())

            abstract = data.get("AbstractText", "").strip()
            source   = data.get("AbstractURL", "")
            heading  = data.get("Heading", "")
            answer   = data.get("Answer", "").strip()      # calculator, conversions, etc.

            parts = []
            if answer:
                parts.append(f"[1] {heading or 'Direct Answer'}\nURL: {source or 'DuckDuckGo'}\nContext: {answer}")
            if abstract:
                parts.append(f"[{len(parts)+1}] {heading}\nURL: {source}\nContext: {abstract}")

            # Related topics as extra context bullets
            topics = data.get("RelatedTopics", [])[:3]
            for i, t in enumerate(topics):
                if isinstance(t, dict) and t.get("Text"):
                    parts.append(
                        f"[{len(parts)+1}] Related\nURL: {t.get('FirstURL','')}\nContext: {t['Text']}"
                    )

            return "\n\n".join(parts)
        except Exception:
            return ""

    # ──────────────────────────────────────────────────────────────────────────
    # DUCKDUCKGO HTML SCRAPER  (general web results — no API key needed)
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _fetch_ddg_html(query: str, max_results: int = 4) -> str:
        """
        Scrapes DuckDuckGo's HTML results page to extract titles + snippets.
        This is the workhorse for news, prices, current events, etc.
        """
        try:
            url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # --- minimal HTML parser (no BeautifulSoup dependency) -----------
            results = []

            # Each result block looks like:
            #   <a class="result__a" href="...">Title</a>
            #   <a class="result__snippet">Snippet text</a>
            title_pattern   = re.compile(r'class="result__a"[^>]*>(.*?)</a>', re.DOTALL)
            snippet_pattern = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)
            url_pattern     = re.compile(r'result__url[^>]*>(.*?)</a>', re.DOTALL)

            titles   = title_pattern.findall(html)
            snippets = snippet_pattern.findall(html)
            urls     = url_pattern.findall(html)

            def strip_tags(text):
                return re.sub(r"<[^>]+>", "", text).strip()

            count = min(max_results, len(titles))
            for i in range(count):
                title   = strip_tags(titles[i])   if i < len(titles)   else "Result"
                snippet = strip_tags(snippets[i]) if i < len(snippets) else ""
                link    = strip_tags(urls[i]).strip() if i < len(urls) else ""
                if title and snippet:
                    results.append(f"[{i+1}] {title}\nURL: {link}\nContext: {snippet}")

            return "\n\n".join(results)

        except Exception as e:
            print(f"[SEARCH DDG HTML WARNING] {e}")
            return ""

    # ──────────────────────────────────────────────────────────────────────────
    # WIKIPEDIA FALLBACK  (stable factual knowledge)
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _fetch_wikipedia(query: str, max_results: int = 2) -> str:
        try:
            url = (
                "https://en.wikipedia.org/w/api.php?action=opensearch"
                f"&search={urllib.parse.quote(query)}&limit={max_results}"
                "&namespace=0&format=json"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "MARVIS-AI-Bot/2.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())

            titles, descriptions, links = data[1], data[2], data[3]
            blocks = []
            for i in range(len(titles)):
                if descriptions[i]:
                    blocks.append(
                        f"[{i+1}] {titles[i]}\nURL: {links[i]}\nContext: {descriptions[i]}"
                    )
            return "\n\n".join(blocks)
        except Exception:
            return ""

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def search_sync(query: str, max_results: int = 4) -> str:
        """
        Master search dispatcher.  Priority chain:
          1. Weather  →  wttr.in (dedicated, always fresh)
          2. DDG Instant Answer  (facts, conversions, quick answers)
          3. DDG HTML scraper  (news, prices, current events, general web)
          4. Wikipedia  (fallback for factual/encyclopaedic queries)
        """
        q_lower = query.lower()

        # 1. Weather branch
        weather_keywords = ["weather", "temperature", "forecast", "humidity", "rain", "climate"]
        if any(kw in q_lower for kw in weather_keywords):
            return WebSearchEngine._fetch_weather(query)

        # 2. DDG Instant Answer (fast facts)
        instant = WebSearchEngine._fetch_ddg_instant(query)

        # 3. DDG HTML (general web / news)
        html_results = WebSearchEngine._fetch_ddg_html(query, max_results)

        # 4. Wikipedia fallback
        wiki = WebSearchEngine._fetch_wikipedia(query, 2) if not html_results else ""

        # Combine: instant answer first, then web results, then wiki
        parts = [p for p in [instant, html_results, wiki] if p.strip()]
        combined = "\n\n".join(parts)

        if not combined.strip():
            return ""

        return combined

    @staticmethod
    def search(query: str, max_results: int = 4):
        """Async-compatible executor wrapper — safe to await in orchestrator."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, WebSearchEngine.search_sync, query, max_results)
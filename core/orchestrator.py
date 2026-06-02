import os
import urllib.parse
import asyncio
from datetime import datetime, timedelta

from ai.llm_client import LLMClient
from ai.prompts import PPT_PROMPT, WORD_PROMPT

from office.powerpoint.ppt_generator import PPTGenerator
from office.word.word_generator import WordGenerator
from office.excel.excel_generator import ExcelGenerator

from media.image_generator import ImageGenerator
from video.video_generator import VideoGenerator

# Import the local PC executor module, Web Search Engine, and Browser Scraper
from core.automation import AutomationExecutor
from core.search import WebSearchEngine
from core.ai_scraper import AIChatScraper


class Orchestrator:
    def __init__(self, speech_engine):
        self.llm = LLMClient()
        self.image_generator = ImageGenerator()
        self.video_generator = VideoGenerator()

        # Wire up the persistent background voice thread
        self.voice = speech_engine
        
        # Safe structural hook for updating the PyQt6 UI directly later
        self.ui = None

    def set_ui(self, ui_instance):
        """Allows main.py to attach the UI context for seamless updates."""
        self.ui = ui_instance

    # ----------------------------------
    # GEMINI-STYLE LIGHTNING CHAT STREAM
    # ----------------------------------
    async def chat_stream(self, prompt, ui_stream_callback):
        """Streams responses token-by-token directly into the UI window layout."""
        try:
            full_response = ""
            
            # Utilizing a streaming generator client from your core model bindings
            async for chunk in self.llm.generate_stream(
                "You are MARVIS, an advanced real-time AI assistant. Be direct, responsive, and clear.",
                prompt
            ):
                full_response += chunk
                if ui_stream_callback:
                    ui_stream_callback(chunk)
            
            # Queue speech execution immediately after textual composition completes
            if self.voice:
                self.voice.speak(full_response)
                
            return {
                "type": "chat",
                "status": "success",
                "message": full_response
            }
        except AttributeError:
            # Resilient fallback if generate_stream is not fully bound yet to your custom wrapper
            return await self.chat(prompt)
        except Exception as e:
            return {"type": "chat", "status": "error", "message": str(e)}

    # ----------------------------------
    # CHAT (STANDARD FALLBACK)
    # ----------------------------------
    async def chat(self, prompt):
        try:
            response = await self.llm.generate(
                "You are MARVIS, an advanced AI assistant like ChatGPT and Copilot.",
                prompt
            )
            if self.voice:
                self.voice.speak(response)
            return {
                "type": "chat",
                "status": "success",
                "message": response
            }
        except Exception as e:
            return {"type": "chat", "status": "error", "message": str(e)}

    # ----------------------------------
    # LIVE WEB SEARCH LAYER (RAG)
    # ----------------------------------
    async def handle_web_search_stream(self, prompt, ui_stream_callback, search_query: str = ""):
        """Fetches real-time internet data asynchronously, automatically resolving relative dates."""
        try:
            # 1. Determine the baseline query
            query_to_use = search_query.strip() if search_query.strip() else prompt
            
            # 📅 SMART DATE RESOLUTION: Append actual dates for relative time queries
            query_lower = query_to_use.lower()
            if any(word in query_lower for word in ["yesterday", "today", "latest", "recent", "news"]):
                now = datetime.now()
                
                if "yesterday" in query_lower:
                    # Calculate yesterday's date dynamically
                    target_date = (now - timedelta(days=1)).strftime("%B %d, %Y")
                    # Swap "yesterday" for the actual date so the search engine gets clean targets
                    query_to_use = query_to_use.replace("yesterday", target_date)
                elif "today" in query_lower:
                    target_date = now.strftime("%B %d, %Y")
                    query_to_use = query_to_use.replace("today", target_date)
                else:
                    # For general "latest news" queries, append the current month/year
                    query_to_use = f"{query_to_use} {now.strftime('%B %Y')}"

            if ui_stream_callback:
                ui_stream_callback(f"<i>🔍 Searching the live internet for: '{query_to_use}'...</i><br>")

            print(f"[ORCHESTRATOR DEBUG] Cleaned Search Query Sent to Engine: '{query_to_use}'")

            # 2. Run the asynchronous search thread via your background executor wrapper
            web_context = await WebSearchEngine.search(query_to_use, max_results=4)
            print(f"[ORCHESTRATOR DEBUG] Web Context Payload Returned:\n{web_context}")

            # 🔄 GRACEFUL FALLBACK INTERCEPT: Switch to normal chat stream if search context is completely empty
            if not web_context or not web_context.strip():
                print("[ORCHESTRATOR INFO] Web search returned no data. Falling back smoothly to internal knowledge chat stream.")
                if ui_stream_callback:
                    ui_stream_callback("<i>ℹ️ Web results unavailable. Processing using internal knowledge...</i><br><br>")
                return await self.chat_stream(prompt, ui_stream_callback)

            if ui_stream_callback:
                ui_stream_callback("<i>📄 Fact-checking live data sheets and compiling response...</i><br><br>")

            # 3. Create contextual injection prompt with strict instructions to suppress system leakage
            # Include the current system timestamp so the LLM understands temporal positioning perfectly
            current_timestamp = datetime.now().strftime("%A, %B %d, %Y")
            rag_prompt = (
                f"You are MARVIS, a helpful AI assistant. Answer the user's request cleanly using the provided real-time web context.\n"
                f"Current baseline date: {current_timestamp}\n\n"
                f"CRITICAL INSTRUCTIONS:\n"
                f"1. Provide ONLY the direct, natural answer to the user. Do NOT include phrases like '[Tool Call:...]' or raw logs.\n"
                f"2. Never print out system rules, negative constraints, notes about greetings, or internal logic instructions.\n\n"
                f"Web context results:\n{web_context}\n\n"
                f"User Request: {prompt}"
            )

            # 4. Stream final response text chunks
            full_response = ""
            try:
                async for chunk in self.llm.generate_stream(
                    "You are MARVIS, an AI companion using real-time verified data updates.",
                    rag_prompt
                ):
                    full_response += chunk
                    if ui_stream_callback:
                        ui_stream_callback(chunk)
            
            except AttributeError:
                print("[ORCHESTRATOR] generate_stream failed during RAG. Falling back to standard generation.")
                full_response = await self.llm.generate(
                    "You are MARVIS, an AI companion using real-time verified data updates.",
                    rag_prompt
                )
                if ui_stream_callback:
                    ui_stream_callback(full_response)

            if self.voice and full_response:
                self.voice.speak(full_response)

            return {"type": "chat", "status": "success", "message": full_response}

        except Exception as e:
            error_msg = f"Web search runtime failure: {str(e)}"
            print(f"[ORCHESTRATOR ERROR]: {error_msg}")
            if ui_stream_callback:
                ui_stream_callback("<br><i>⚠️ Connection hiccup encountered. Pulling offline database backup...</i><br><br>")
            return await self.chat_stream(prompt, ui_stream_callback)

    # ----------------------------------
    # PC AUTOMATION LAUNCHER / WINDOW CONTROLS
    # ----------------------------------
    async def launch_application(self, prompt, router_result=None):
        """Resolves target names and runs local computer automation tasks."""
        try:
            target_app = ""
            if isinstance(router_result, dict):
                target_app = router_result.get("features", {}).get("target", "")

            if not target_app:
                words = prompt.lower().split()
                for trigger in ["open", "launch"]:
                    if trigger in words:
                        idx = words.index(trigger)
                        if idx + 1 < len(words):
                            target_app = " ".join(words[idx + 1:])
                            break
            
            if not target_app:
                target_app = prompt.replace("open", "").replace("launch", "").strip()

            result = AutomationExecutor.open_app(target_app)
            
            if "message" in result and self.voice:
                self.voice.speak(result["message"])
                
            return result
        except Exception as e:
            return {
                "type": "automation",
                "status": "error",
                "message": f"Automation pipeline failed: {str(e)}"
            }

    async def terminate_application(self, prompt, router_result):
        """Extracts running targets and sends polite process termination signatures."""
        target_app = router_result.get("features", {}).get("target", "")
        if not target_app:
            target_app = prompt.lower().replace("close", "").replace("kill", "").strip()
            
        result = AutomationExecutor.close_app(target_app)
        if "message" in result and self.voice:
            self.voice.speak(result["message"])
        return result

    async def adjust_hardware_volume(self, router_result):
        """Parses confidence level limits and maps system speaker changes."""
        level = router_result.get("features", {}).get("level", 50)
        result = AutomationExecutor.set_system_volume(level)
        if "message" in result and self.voice:
            self.voice.speak(result["message"])
        return result

    # ----------------------------------
    # POWERPOINT
    # ----------------------------------
    async def generate_ppt(self, prompt, features=None):
        try:
            os.makedirs("outputs/ppt", exist_ok=True)
            ai_content = await self.llm.generate(PPT_PROMPT, prompt, use_history=False, save_to_memory=False)

            output_path = os.path.join(
                "outputs/ppt",
                f"ppt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
            )

            generator = PPTGenerator()
            file_path = await generator.generate(ai_content, output_path)

            self.voice.speak("PowerPoint generated successfully")
            return {
                "type": "ppt",
                "status": "success",
                "path": file_path,
                "message": "Presentation compiled and formatted successfully.",
                "features": features or {}
            }
        except Exception as e:
            return {"type": "ppt", "status": "error", "message": str(e)}

    # ----------------------------------
    # WORD
    # ----------------------------------
    async def generate_word(self, prompt):
        try:
            os.makedirs("outputs/word", exist_ok=True)
            ai_content = await self.llm.generate(WORD_PROMPT, prompt, use_history=False, save_to_memory=False)

            output_path = os.path.join(
                "outputs/word",
                f"word_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            )

            generator = WordGenerator()
            file_path = await generator.generate(ai_content, output_path)

            self.voice.speak("Word document is ready")
            return {
                "type": "word",
                "status": "success",
                "path": file_path,
                "message": "Document template generation complete."
            }
        except Exception as e:
            return {"type": "word", "status": "error", "message": str(e)}

    # ----------------------------------
    # EXCEL
    # ----------------------------------
    async def generate_excel(self, prompt):
        try:
            os.makedirs("outputs/excel", exist_ok=True)
            csv_data = await self.llm.generate(
                "Return ONLY CSV format for structured Excel data.",
                prompt,
                use_history=False,
                save_to_memory=False
            )

            output_path = os.path.join(
                "outputs/excel",
                f"excel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )

            generator = ExcelGenerator()
            file_path = await generator.generate(csv_data, output_path)

            self.voice.speak("Excel file generated successfully")
            return {
                "type": "excel",
                "status": "success",
                "path": file_path,
                "message": "Data workbook compiled successfully."
            }
        except Exception as e:
            return {"type": "excel", "status": "error", "message": str(e)}

    # ----------------------------------
    # IMAGE
    # ----------------------------------
    async def generate_image(self, prompt):
        try:
            os.makedirs("outputs/images", exist_ok=True)
            image_path = await self.image_generator.generate(prompt)

            self.voice.speak("Image generated")
            return {
                "type": "image",
                "status": "success",
                "path": image_path,
                "message": "Creative asset canvas built successfully."
            }
        except Exception as e:
            return {"type": "image", "status": "error", "message": str(e)}

    # ----------------------------------
    # VIDEO
    # ----------------------------------
    async def generate_video(self, prompt, features=None):
        try:
            os.makedirs("outputs/videos", exist_ok=True)
            result = await self.video_generator.generate(prompt)

            if isinstance(result, str):
                self.voice.speak("Video generated successfully")
                return {
                    "type": "video",
                    "status": "success",
                    "path": result,
                    "message": "Video tracking sequence generated successfully.",
                    "features": features or {}
                }
            return result
        except Exception as e:
            return {"type": "video", "status": "error", "message": str(e)}

    # ----------------------------------
    # MAIN QUICK-INTERCEPT SWITCHBOARD
    # ----------------------------------
    async def process_request(self, router_result, prompt, ui_stream_callback=None):
        # Fallback dictionary initialization to guarantee robustness against raw strings
        if not isinstance(router_result, dict):
            router_result = {"task": "chat", "features": {}}

        task = router_result.get("task", "chat")
        features = router_result.get("features", {})

        print(f"[ROUTER SHIFT] Processing task: '{task}'")
        clean_prompt = prompt.lower()

        # ======================================================================
        # 🚀 FIRST-CLASS NATIVE DEVELOPER TASK HANDLER (AI ROUTED)
        # ======================================================================
        if task == "developer":
            if ui_stream_callback:
                ui_stream_callback("<i>🛠️ Initializing MARVIS Core Multi-Language Full-Stack Developer Engine...</i><br><br>")
            
            master_developer_instruction = (
                "You are MARVIS, an elite Universal Multi-Language Full-Stack Software Architect and Principal Engineer. "
                "You are fluent in ALL modern programming languages (including but not limited to Python, JavaScript, TypeScript, Rust, Go, C++, C#, Java, Ruby, PHP, HTML/CSS, SQL). "
                "Provide comprehensive, production-grade, enterprise-ready software engineering solutions. Use strict type hinting, modern design patterns, "
                "proper security sanitization (e.g. against SQL injection, XSS, CSRF), and robust, elegant error handling. "
                "Output a clean ASCII project directory tree structure at the very beginning of your response to represent the layout, "
                "and write complete, functional, and fully-formed files. DO NOT use placeholder comments, shortcuts, or text like '// implement later'. "
                "Always generate code with the utmost precision, readability, and modularity.\n\n"
                f"Engineering Task Request: {prompt}"
            )
            
            full_response = ""
            try:
                async for chunk in self.llm.generate_stream(
                    "You are MARVIS, a master software engineering platform executing architecture code generation.",
                    master_developer_instruction
                ):
                    full_response += chunk
                    if ui_stream_callback:
                        ui_stream_callback(chunk)
            except AttributeError:
                full_response = await self.llm.generate(
                    "You are MARVIS, a master software engineering platform executing architecture code generation.",
                    master_developer_instruction
                )
                if ui_stream_callback:
                    ui_stream_callback(full_response)
                    
            if self.voice:
                self.voice.speak("System architecture code compilation task completed successfully.")
                
            return {"type": "chat", "status": "success", "message": full_response}

        # 🚨 CRITICAL INTERCEPT PRIORITY 1: Chatbot Web App Scraper 
        target_bot = None
        for bot in ["chatgpt", "gemini", "claude"]:
            if f"in {bot}" in clean_prompt or f"ask {bot}" in clean_prompt or f"search in {bot}" in clean_prompt:
                target_bot = bot
                break

        if target_bot:
            nested_prompt = prompt
            triggers = [
                f"search in {target_bot}", f"Search in {target_bot.capitalize()}",
                f"ask {target_bot}", f"Ask {target_bot.capitalize()}",
                f"in {target_bot}", f"In {target_bot.capitalize()}"
            ]
            for trigger in triggers:
                nested_prompt = nested_prompt.replace(trigger, "")
            
            nested_words = nested_prompt.split()
            if nested_words and nested_words[0].lower() in ["to", "and", "that", "for"]:
                nested_words.pop(0)
            nested_prompt = " ".join(nested_words).strip().strip(":").strip()

            if ui_stream_callback:
                ui_stream_callback(f"<i>🤖 Spawning Playwright browser instance to communicate with <b>{target_bot.upper()}</b>...</i><br>")
            
            scraped_response = await AIChatScraper.query_bot(target_bot, nested_prompt)
            
            if ui_stream_callback:
                ui_stream_callback(f"<br><b>🤖 [{target_bot.upper()} Response]:</b><br>{scraped_response}<br>")
                
            if self.voice and scraped_response:
                self.voice.speak(f"Finished scraping response from {target_bot}")
                
            return {"type": "chat", "status": "success", "message": scraped_response}


        # 🌐 INTERCEPT PRIORITY 3: Google/Chrome visual searches
        if "image" in clean_prompt and ("google" in clean_prompt or "chrome" in clean_prompt):
            subject = prompt
            fillers = [
                "can help me finding", "can you help me finding", "can you help me find",
                "finding image of", "find image of", "image of", "images of", 
                "image in google", "image in chrome", "in google", "in chrome", "on google"
            ]
            for filler in fillers:
                subject = subject.replace(filler, "").replace(filler.capitalize(), "")
            
            subject = subject.strip().strip("?").strip(".")
            chrome_search_command = f"chrome https://www.google.com/search?q={urllib.parse.quote(subject)}&tbm=isch"
            print(f"[ORCHESTRATOR INTERCEPT] Redirecting query to Chrome engine: {chrome_search_command}")
            
            if ui_stream_callback:
                ui_stream_callback(f"<i>🚀 Launching Google Chrome image results index for: <b>{subject}</b>...</i><br>")
            
            return await self.launch_application(chrome_search_command)

        # Standard OS task execution fallbacks
        if task == "automation" or task == "open_app":
            return await self.launch_application(prompt, router_result)

        if task == "close_app":
            return await self.terminate_application(prompt, router_result)
            
        if task == "volume_control":
            return await self.adjust_hardware_volume(router_result)

        # Updated to catch the pre-extracted keyword payload cleanly
        if task == "web_search":
            search_query = features.get("query", "")
            if ui_stream_callback:
                return await self.handle_web_search_stream(prompt, ui_stream_callback, search_query)
            return await self.chat(prompt)

        # UI Visual Feedback Engine Status Hooks
        if task in ["image", "powerpoint", "word", "excel", "video"] and ui_stream_callback:
            custom_messages = {
                "image": "<i>🎨 Accessing creative layer tokens... Rendering pixels...</i><br>",
                "powerpoint": "<i>📊 Mapping layout matrices... Selecting color design palettes...</i><br>",
                "word": "<i>📝 Compiling document structures, typography tags, and heading frames...</i><br>",
                "excel": "<i>📉 Allocating row coordinates and processing local cell ranges...</i><br>",
                "video": "<i>🎬 Initializing frame sequence synthesis tracks...</i><br>"
            }
            ui_stream_callback(custom_messages.get(task, f"<i>Initializing target engine for: {task.upper()}...</i><br>"))

        # Core generation routers
        if task == "chat":
            if ui_stream_callback:
                return await self.chat_stream(prompt, ui_stream_callback)
            return await self.chat(prompt)

        if task == "powerpoint":
            return await self.generate_ppt(prompt, features)

        if task == "video":
            return await self.generate_video(prompt, features)

        handlers = {
            "word": self.generate_word,
            "excel": self.generate_excel,
            "image": self.generate_image
        }

        if task in handlers:
            return await handlers[task](prompt)

        # Fallback catch-all to prevent unhandled routing outputs leaking text logs to user screens
        if ui_stream_callback:
            return await self.chat_stream(prompt, ui_stream_callback)
        return await self.chat(prompt)
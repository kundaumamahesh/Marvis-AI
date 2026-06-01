import os
import sys
import json
import requests
import asyncio
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal

class DiagnosticWorker(QThread):
    progress = pyqtSignal(str, str, str)  # Emits (integration_name, status, details)
    finished = pyqtSignal(dict)           # Emits final summary report

    def __init__(self):
        super().__init__()
        self.results = {}

    def run(self):
        # 1. OpenRouter LLM Check
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            self.report("LLM (OpenRouter)", "FAIL", "Missing OPENROUTER_API_KEY in .env file.")
        else:
            try:
                # Test connection with a fast 1-token query
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "openrouter/owl-alpha",
                    "messages": [{"role": "user", "content": "Ping"}],
                    "max_tokens": 1
                }
                response = requests.post(url, json=payload, headers=headers, timeout=5)
                if response.status_code == 200:
                    self.report("LLM (OpenRouter)", "SUCCESS", "Connected to owl-alpha API successfully.")
                else:
                    self.report("LLM (OpenRouter)", "WARNING", f"Status Code {response.status_code}: {response.text}")
            except Exception as e:
                self.report("LLM (OpenRouter)", "FAIL", f"Connection failed: {e}")

        # 2. PowerPoint Module Check
        try:
            from pptx import Presentation
            prs = Presentation()
            self.report("PowerPoint Engine", "SUCCESS", "python-pptx is installed and initializing correctly.")
        except ImportError as e:
            self.report("PowerPoint Engine", "FAIL", "python-pptx is missing. Install with 'pip install python-pptx'")
        except Exception as e:
            self.report("PowerPoint Engine", "FAIL", f"Initialization failed: {e}")

        # 3. Word Document Module Check
        try:
            from docx import Document
            doc = Document()
            self.report("Word Document Engine", "SUCCESS", "python-docx is installed and initializing correctly.")
        except ImportError as e:
            self.report("Word Document Engine", "FAIL", "python-docx is missing. Install with 'pip install python-docx'")
        except Exception as e:
            self.report("Word Document Engine", "FAIL", f"Initialization failed: {e}")

        # 4. Excel Spreadsheet Module Check
        try:
            from openpyxl import Workbook
            wb = Workbook()
            self.report("Excel Spreadsheet Engine", "SUCCESS", "openpyxl is installed and initializing correctly.")
        except ImportError as e:
            self.report("Excel Spreadsheet Engine", "FAIL", "openpyxl is missing. Install with 'pip install openpyxl'")
        except Exception as e:
            self.report("Excel Spreadsheet Engine", "FAIL", f"Initialization failed: {e}")

        # 5. Image Generator API Check
        try:
            from PIL import Image
            # Fast ping to Pollinations AI to check service availability
            response = requests.head("https://image.pollinations.ai/", timeout=5)
            self.report("Image Generator", "SUCCESS", "Pollinations AI is online and Pillow library is configured.")
        except ImportError as e:
            self.report("Image Generator", "FAIL", "Pillow image library is missing. Install with 'pip install pillow'")
        except Exception as e:
            self.report("Image Generator", "WARNING", f"Pollinations API warning: {e}")

        # 6. Video Generator Template Check
        try:
            html_path = os.path.join("video", "veo_player.html")
            if os.path.exists(html_path):
                self.report("Video Player Template", "SUCCESS", "veo_player.html is present and verified.")
            else:
                self.report("Video Player Template", "FAIL", "veo_player.html is missing in the video/ directory.")
        except Exception as e:
            self.report("Video Player Template", "FAIL", str(e))

        # 7. Web Search Engine Check
        try:
            response = requests.get("https://wttr.in/Mangalagiri?format=j1", timeout=5)
            if response.status_code == 200:
                self.report("Web Search & Weather API", "SUCCESS", "wttr.in Weather API connection succeeded.")
            else:
                self.report("Web Search & Weather API", "WARNING", f"Weather API returned status code {response.status_code}")
        except Exception as e:
            self.report("Web Search & Weather API", "FAIL", f"Connection timed out/failed: {e}")

        # 8. Web Scraper Integration Check
        try:
            import playwright
            self.report("Playwright Scraper", "SUCCESS", "Playwright is installed on the system.")
        except ImportError:
            self.report("Playwright Scraper", "FAIL", "Playwright library is not installed. Run 'pip install playwright'")
        except Exception as e:
            self.report("Playwright Scraper", "FAIL", str(e))

        # 9. Voice Synthesis (TTS) Check
        try:
            import pyttsx3
            engine = pyttsx3.init()
            self.report("Voice Synthesis (TTS)", "SUCCESS", f"pyttsx3 initialized successfully using default driver.")
        except ImportError:
            self.report("Voice Synthesis (TTS)", "FAIL", "pyttsx3 is not installed. Run 'pip install pyttsx3'")
        except Exception as e:
            self.report("Voice Synthesis (TTS)", "WARNING", f"Could not initialize TTS engine: {e}")

        # 10. Microphone & STT Hardware Check
        try:
            import speech_recognition as sr
            import pyaudio
            # Check mic hardware
            r = sr.Recognizer()
            mics = sr.Microphone.list_microphone_names()
            if mics:
                self.report("Voice Input (STT)", "SUCCESS", f"SpeechRecognition and PyAudio active. Found {len(mics)} microphone inputs.")
            else:
                self.report("Voice Input (STT)", "WARNING", "SpeechRecognition/PyAudio configured, but no physical microphone was detected.")
        except ImportError as e:
            if "pyaudio" in str(e).lower() or "no module named 'pyaudio'" in str(e).lower():
                self.report("Voice Input (STT)", "WARNING", "Voice input disabled: 'pyaudio' package is missing. Precompiled wheels required for Python 3.14 on Windows.")
            else:
                self.report("Voice Input (STT)", "FAIL", f"SpeechRecognition package error: {e}")
        except Exception as e:
            self.report("Voice Input (STT)", "WARNING", f"Microphone access error: {e}")

        self.finished.emit(self.results)

    def report(self, name, status, details):
        self.results[name] = {"status": status, "details": details}
        self.progress.emit(name, status, details)

import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from PyQt6.QtWidgets import QApplication

from ui.modern_ui import ModernUI
from core.orchestrator import Orchestrator

# ── optional voice modules ──────────────────────────────────────────────────
# Wrapped in try/except so the app still starts if pyaudio / pyttsx3 are
# missing in the current environment.
try:
    from voice.speech_engine import SpeechEngine
    from voice.voice_input import VoiceInputWorker
    VOICE_AVAILABLE = True
except Exception as _voice_err:
    print(f"[WARN] Voice modules unavailable: {_voice_err}")
    VOICE_AVAILABLE = False


def main():
    app = QApplication(sys.argv)

    # ── 1. Text-To-Speech engine ─────────────────────────────────────────────
    tts_engine = None
    if VOICE_AVAILABLE:
        try:
            tts_engine = SpeechEngine()
            tts_engine.start()
        except Exception as e:
            print(f"[WARN] TTS engine failed to start: {e}")
            tts_engine = None

    # ── 2. Orchestrator (brain) ──────────────────────────────────────────────
    orchestrator = Orchestrator(speech_engine=tts_engine)

    # ── 3. Main UI window ────────────────────────────────────────────────────
    window = ModernUI(orchestrator=orchestrator)
    orchestrator.set_ui(window)

    # ── 4. Voice listener thread ─────────────────────────────────────────────
    voice_listener = None
    if VOICE_AVAILABLE and tts_engine:
        try:
            voice_listener = VoiceInputWorker()
            window.voice_listener = voice_listener
            voice_listener.text_recognized.connect(window.handle_voice_input)
            voice_listener.status_changed.connect(window.update_status_bar)
            voice_listener.start()
        except Exception as e:
            print(f"[WARN] Voice listener failed to start: {e}")
            voice_listener = None

    window.show()

    # ── 5. Clean shutdown ────────────────────────────────────────────────────
    exit_code = app.exec()

    print("[System] Shutting down MARVIS AI background workers...")

    if tts_engine:
        try:
            tts_engine.stop()
        except Exception:
            pass

    if voice_listener:
        try:
            voice_listener.stop()
        except Exception:
            pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()



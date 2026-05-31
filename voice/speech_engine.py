import pyttsx3
import threading
import queue
import time
import sys

class SpeechEngine(threading.Thread):
    def __init__(self):
        super().__init__()
        self.speech_queue = queue.Queue()
        self.daemon = True  # Kills this thread automatically when the PyQt6 window closes
        self._stop_event = threading.Event()
        self.engine = None
        
        # New: Callbacks to hook into the UI for microphone auto-muting
        self.on_start_callback = None
        self.on_end_callback = None

    def set_callbacks(self, on_start, on_end):
        """Links UI hooks so the microphone can auto-pause when MARVIS speaks."""
        self.on_start_callback = on_start
        self.on_end_callback = on_end

    def stop_speaking(self):
        """Force stops the current audio playback loop instantly and clears the queue."""
        print("[TTS] Interrupt triggered! Clearing queue and stopping playback...")
        
        # Clear out any pending text blocks waiting in the queue
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except queue.Empty:
                break
        
        # Break the native engine's current loop
        if self.engine:
            try:
                self.engine.stop()
            except Exception as e:
                print(f"[TTS STOP ERROR] Failed to stop native engine: {e}", file=sys.stderr)
        
        # Explicitly invoke the end callback to unmute the microphone button immediately
        if self.on_end_callback:
            self.on_end_callback()

    def run(self):
        """
        Runs continuously in the background. Initializes the COM engine 
        strictly inside this thread's own execution context.
        """
        print("[TTS] Initializing pyttsx3 engine background thread...")
        try:
            # Initialize inside the worker thread context
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 175)
            print("[TTS] Engine successfully initialized and ready.")
        except Exception as e:
            print(f"[CRITICAL TTS ERROR] Could not initialize engine: {e}", file=sys.stderr)
            return

        while not self._stop_event.is_set():
            try:
                # Grab text from the queue. Timeout keeps the loop alive to check stop events.
                text = self.speech_queue.get(timeout=0.5)
                if text is None:
                    break
                
                print(f"[TTS] Speaking: '{text[:30]}...'")
                
                # 1. Fire the start callback to update the UI button to "🤖 Speaking..." and mute the mic
                if self.on_start_callback:
                    self.on_start_callback()
                
                # Execute speech blocks safely
                self.engine.say(text)
                self.engine.runAndWait()
                
                # 2. Fire the end callback to reset the UI button back to normal
                if self.on_end_callback:
                    self.on_end_callback()
                
                # Small cool-down to let the native audio device release
                time.sleep(0.1)
                self.speech_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TTS RUN ERROR] Error during playback loop: {e}", file=sys.stderr)
                
                # Fire the end callback so the UI doesn't lock up if the engine glitches out
                if self.on_end_callback:
                    self.on_end_callback()
                    
                # Attempt structural engine reset if it encounters a catastrophic crash
                try:
                    self.engine = pyttsx3.init()
                    self.engine.setProperty("rate", 175)
                except:
                    pass

    def speak(self, text):
        """
        Thread-safe method called by your Orchestrator. 
        Drops text into the queue and goes back to work instantly.
        """
        if not text or not text.strip():
            return
        
        # Strip markdown syntax out so MARVIS doesn't try to pronounce asterisks
        clean_text = text.replace("**", "").replace("*", "").replace("`", "").strip()
        
        print(f"[TTS] Queueing text: '{clean_text[:30]}...'")
        self.speech_queue.put(clean_text)

    def stop(self):
        """Stops the loop and terminates the background thread cleanly."""
        self._stop_event.set()
        self.speech_queue.put(None)
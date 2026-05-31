import speech_recognition as sr
from PyQt6.QtCore import QThread, pyqtSignal
import time
import sys

class VoiceInputWorker(QThread):
    # Safe cross-thread signals for PyQt6
    text_recognized = pyqtSignal(str)
    status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_running = True         # Keeps background QThread alive
        self.active_listening = False   # Flag changed by the UI Mic Button
        
        # Optimize recognizer settings for snappy interaction
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.energy_threshold = 300
        self.recognizer.pause_threshold = 0.8
        
        # Safe microphone initialization
        try:
            self.microphone = sr.Microphone()
        except Exception as e:
            print(f"[CRITICAL MIC ERROR] Audio hardware missing or blocked: {e}", file=sys.stderr)

    def start_listening(self):
        """Explicitly called by ModernUI when mic button is toggled ON."""
        if self.microphone is None:
            self.status_changed.emit("Hardware Error: No Mic Found")
            return
        self.active_listening = True

    def stop_listening(self):
        """Explicitly called by ModernUI when mic button is toggled OFF."""
        self.active_listening = False
        self.status_changed.emit("Ready")

    def run(self):
        """Continuous thread lifecycle loop."""
        if self.microphone is None:
            self.status_changed.emit("Status: Mic Disabled")
            return

        # Use the mic device context safely inside the background thread
        try:
            with self.microphone as source:
                self.status_changed.emit("Calibrating background noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.status_changed.emit("Ready")
                
                while self.is_running:
                    # If UI hasn't toggled the mic button on, sit tight and rest CPU
                    if not self.active_listening:
                        time.sleep(0.1)
                        continue
                    
                    try:
                        self.status_changed.emit("Listening...")
                        # Capture audio chunk with a 10 second maximum limit per phrase
                        audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=10)
                        
                        # Stop capturing immediately once a single complete thought is captured
                        self.active_listening = False
                        
                        self.status_changed.emit("Processing speech...")
                        # Transcribe via Google STT engine
                        text = self.recognizer.recognize_google(audio)
                        
                        if text.strip():
                            self.text_recognized.emit(text)
                            
                    except sr.UnknownValueError:
                        # Clear state gracefully if it's just ambient room noise/coughing
                        self.status_changed.emit("Ready (No speech detected)")
                        self.active_listening = False
                    except sr.WaitTimeoutError:
                        self.active_listening = False
                        self.status_changed.emit("Ready")
                    except Exception as e:
                        print(f"[STT Loop Exception] {e}", file=sys.stderr)
                        self.active_listening = False
                        self.status_changed.emit("Ready")
                        
        except Exception as e:
            print(f"[STT Hardware Crash] Could not open mic source: {e}", file=sys.stderr)
            self.status_changed.emit("System Error: Mic unavailable")

    def stop(self):
        """Stops the lifecycle loop cleanly on application exit."""
        self.is_running = False
        self.active_listening = False
        self.quit()
        self.wait()
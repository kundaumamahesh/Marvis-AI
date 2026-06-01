import os
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QLineEdit,
    QLabel,
    QListWidget,
    QHBoxLayout
)
from PyQt6.QtCore import pyqtSlot, QMetaObject, Qt
import subprocess
from subprocess import CREATE_NEW_PROCESS_GROUP

from core.router import Router
from core.workers import Worker
from core.diagnostics import DiagnosticWorker


class ModernUI(QWidget):

    def __init__(self, orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.worker = None  
        self.voice_listener = None 
        self.is_first_token = True  # Track streaming states for text box cleanup
        self.setup_ui()

        # Look for 'voice' attribute to match the Orchestrator's initialization
        if hasattr(self.orchestrator, 'voice') and self.orchestrator.voice:
            self.orchestrator.voice.set_callbacks(
                on_start=lambda: QMetaObject.invokeMethod(self, "tts_started_speaking", Qt.ConnectionType.QueuedConnection),
                on_end=lambda: QMetaObject.invokeMethod(self, "tts_finished_speaking", Qt.ConnectionType.QueuedConnection)
            )

    def setup_ui(self):
        self.setWindowTitle("MARVIS AI")
        self.resize(1600, 1000)

        self.setStyleSheet("""
        QWidget {
            background-color: #0b0f19;
            color: white;
            font-family: "Segoe UI", sans-serif;
        }

        QTextEdit {
            background: #111827;
            border-radius: 20px;
            border: 2px solid cyan;
            padding: 20px;
            font-size: 15px;
        }

        QLineEdit {
            background: #111827;
            border-radius: 18px;
            border: 2px solid cyan;
            padding: 16px;
            font-size: 15px;
        }

        QPushButton {
            background: cyan;
            color: black;
            border-radius: 18px;
            padding: 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: #00cccc;
        }

        QListWidget {
            background: #111827;
            border-radius: 18px;
            border: 2px solid cyan;
            padding: 10px;
        }

        QLabel {
            font-size: 16px;
            font-weight: bold;
            color: cyan;
        }
        """)

        main_layout = QHBoxLayout()

        # Sidebar
        sidebar_layout = QVBoxLayout()
        self.history = QListWidget()
        sidebar_layout.addWidget(QLabel("Chats"))
        sidebar_layout.addWidget(self.history)
        self.check_integration_btn = QPushButton("Check Integrations")
        self.check_integration_btn.clicked.connect(self.run_integrations_check)
        sidebar_layout.addWidget(self.check_integration_btn)
        self.dev_server_btn = QPushButton("Start Dev Server")
        self.dev_server_btn.clicked.connect(self.start_dev_server)
        sidebar_layout.addWidget(self.dev_server_btn)

        # Main area
        content_layout = QVBoxLayout()

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)

        # Controls Layout Row
        input_layout = QHBoxLayout()
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("Talk with MARVIS...")
        self.input.returnPressed.connect(self.process)

        # 🎙️ MIC BUTTON
        self.mic_button = QPushButton("🎤 Mic: Off")
        self.mic_button.setFixedWidth(130)
        self.mic_button.setCheckable(True)  
        self.mic_button.clicked.connect(self.toggle_voice)

        # 🛑 INTERRUPT/STOP BUTTON
        self.stop_button = QPushButton("🛑 Stop Audio")
        self.stop_button.setFixedWidth(130)
        self.stop_button.setStyleSheet("""
            QPushButton { background: #374151; color: white; border-radius: 18px; }
            QPushButton:hover { background: #4b5563; }
        """)
        self.stop_button.clicked.connect(self.interrupt_marvis)
        
        input_layout.addWidget(self.input, 4)
        input_layout.addWidget(self.mic_button, 1)
        input_layout.addWidget(self.stop_button, 1)

        self.button = QPushButton("Generate")
        self.button.clicked.connect(self.process)

        # Status Bar
        self.status_label = QLabel("System Status: Ready")
        self.status_label.setStyleSheet("font-size: 13px; color: #55f3ff; font-weight: normal; padding-left: 5px;")

        content_layout.addWidget(self.chat)
        content_layout.addLayout(input_layout)
        content_layout.addWidget(self.button)
        content_layout.addWidget(self.status_label)

        main_layout.addLayout(sidebar_layout, 1)
        main_layout.addLayout(content_layout, 4)

        self.setLayout(main_layout)

    # -------------------------
    # INTERRUPT HANDLER
    # -------------------------
    def interrupt_marvis(self):
        """Forces the speech engine to shut up instantly."""
        if hasattr(self.orchestrator, 'voice') and self.orchestrator.voice:
            self.orchestrator.voice.stop_speaking()
            self.status_label.setText("System Status: Audio Interrupted")

    # -------------------------
    # SELF-HEARING PREVENTION HOOKS
    # -------------------------
    @pyqtSlot()
    def tts_started_speaking(self):
        """Fires safely inside the main thread when MARVIS opens its mouth."""
        if self.voice_listener:
            self.voice_listener.stop_listening()
        self.mic_button.setEnabled(False)
        self.mic_button.setText("🤖 Speaking...")

    @pyqtSlot()
    def tts_finished_speaking(self):
        """Fires safely inside the main thread when MARVIS finishes speaking."""
        self.mic_button.setEnabled(True)
        self.reset_mic_button()

    # -------------------------
    # MIC TOGGLE HANDLER
    # -------------------------
    def toggle_voice(self):
        if self.mic_button.isChecked():
            self.mic_button.setText("🔴 Listening...")
            self.mic_button.setStyleSheet("""
                QPushButton { background: #ff3333; color: white; border-radius: 18px; font-weight: bold; }
                QPushButton:hover { background: #cc2222; }
            """)
            if self.voice_listener:
                self.voice_listener.start_listening()
        else:
            self.reset_mic_button()
            if self.voice_listener:
                self.voice_listener.stop_listening()

    def reset_mic_button(self):
        self.mic_button.setChecked(False)
        self.mic_button.setText("🎤 Mic: Off")
        self.mic_button.setStyleSheet("") 

    # -------------------------
    # INPUT HANDLERS
    # -------------------------
    def process(self):
        prompt = self.input.text().strip()
        if not prompt:
            return
        self.input.clear()
        self.chat.append(f"<br><b>You:</b> {prompt}")
        self.chat.append("<span style='color: #55f3ff;'><b>MARVIS:</b> Thinking...</span>")
        self.run_pipeline(prompt)

    @pyqtSlot(str)
    def handle_voice_input(self, prompt):
        self.reset_mic_button()
        if not prompt or not prompt.strip():
            return
        self.chat.append(f"<br><b>You (Voice):</b> {prompt}")
        self.chat.append("<span style='color: #55f3ff;'><b>MARVIS:</b> Thinking...</span>")
        self.run_pipeline(prompt)

    # ----------------------------------
    # NON-BLOCKING PIPELINE RUNNER
    # ----------------------------------
    def run_pipeline(self, prompt):
        # Reset token state tracker for every brand new request track loop
        self.is_first_token = True

        # Pass function references and raw parameters to decouple cross-thread setup loops
        self.worker = Worker(self.handle_request, prompt)

        # Connect both our completion tracker and the newly engineered real-time token signal
        self.worker.token_streamed.connect(self.append_stream_token)
        self.worker.finished.connect(self.completed)
        self.worker.start()

    @pyqtSlot()
    def run_integrations_check(self):
        self.status_label.setText("System Status: Running integration checks...")
        self.diagnostic_worker = DiagnosticWorker()
        self.diagnostic_worker.progress.connect(self.handle_integration_progress)
        self.diagnostic_worker.finished.connect(self.handle_integration_finished)
        self.diagnostic_worker.start()

    @pyqtSlot(str, str, str)
    def handle_integration_progress(self, name, status, details):
        self.chat.append(f"<b>{name}:</b> {status} - {details}")

    @pyqtSlot(dict)
    def handle_integration_finished(self, results):
        self.chat.append("<b>Integration Check Completed</b>")
        for name, info in results.items():
            self.chat.append(f"{name}: {info['status']} - {info['details']}")
        self.status_label.setText("System Status: Ready")

    @pyqtSlot()
    def start_dev_server(self):
        """Launch a simple HTTP server serving the UI folder."""
        self.status_label.setText("System Status: Starting dev server on http://localhost:8000")
        server_dir = os.path.abspath(os.path.join(os.getcwd(), "ui"))
        subprocess.Popen(
            ["python", "-m", "http.server", "8000"],
            cwd=server_dir,
            creationflags=CREATE_NEW_PROCESS_GROUP,
        )
        self.chat.append("<i>Dev server started at http://localhost:8000</i>")
    async def handle_request(self, prompt, ui_stream_callback=None):
        result = await Router.detect(prompt)
        return await self.orchestrator.process_request(result, prompt, ui_stream_callback)

    def clear_thinking_placeholder(self):
        """Safely removes the 'MARVIS: Thinking...' placeholder line from the layout text."""
        cursor = self.chat.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.movePosition(cursor.MoveOperation.StartOfLine, cursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

    @pyqtSlot(str)
    def append_stream_token(self, token):
        """Fires instantly every single time a character chunk drops from the pipeline."""
        if self.is_first_token:
            self.clear_thinking_placeholder()
            self.chat.append("<b>MARVIS:</b> ")
            self.is_first_token = False

        # Inject incoming text segments seamlessly without appending hard line breaks
        cursor = self.chat.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat.setTextCursor(cursor)
        self.chat.insertHtml(token)
        self.chat.ensureCursorVisible()

    @pyqtSlot(object)
    def completed(self, result):
        # Handle structural dictionary responses safely
        if isinstance(result, dict):
            rtype = result.get("type", "")
            message = result.get("message", "")
            path = result.get("path", "")

            if rtype == "chat":
                # Fallback print logic check if text-streaming wasn't utilized
                if self.is_first_token:
                    self.clear_thinking_placeholder()
                    self.chat.append(f"<b>MARVIS:</b> {message}")
            elif rtype == "automation":
                self.clear_thinking_placeholder()
                self.chat.append(f"<span style='color: #00ffcc;'><b>[System Action]:</b> {message}</span>")
            elif path:
                self.clear_thinking_placeholder()
                self.chat.append(f"<b>MARVIS:</b> {rtype.upper()} generated successfully.")
                self.chat.append(f"<span style='color: gray;'>File path: {path}</span>")
                if os.path.exists(path):
                    os.startfile(path)
            else:
                if self.is_first_token:
                    self.clear_thinking_placeholder()
                    self.chat.append(f"<b>MARVIS:</b> {message}")
        else:
            if self.is_first_token:
                self.clear_thinking_placeholder()
                self.chat.append(f"<b>MARVIS:</b> {result}")
            
        self.chat.ensureCursorVisible()

    @pyqtSlot(str)
    def update_status_bar(self, status_text):
        self.status_label.setText(f"System Status: {status_text}")
        if "Processing" in status_text or "Error" in status_text:
            self.reset_mic_button()
import os
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QLineEdit,
    QLabel,
    QListWidget,
    QHBoxLayout,
    QProgressBar,
)
from PyQt6.QtCore import QTimer, pyqtSlot, QMetaObject, Qt

import subprocess
from subprocess import CREATE_NEW_PROCESS_GROUP

from core.router import Router
from core.workers import Worker
from core.diagnostics import DiagnosticWorker
from ui.ui.markdown_renderer import MarkdownRenderer


class ModernUI(QWidget):

    def __init__(self, orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.worker = None  
        self.voice_listener = None 
        self.is_first_token = True  # Track streaming states for text box cleanup
        self.chat_messages = []     # Track modern visual chat history
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
            background-color: #080b11;
            color: #e2e8f0;
            font-family: "Outfit", "Segoe UI", sans-serif;
        }

        QTextEdit {
            background: rgba(15, 23, 42, 0.65);
            border-radius: 16px;
            border: 1px solid rgba(6, 182, 212, 0.15);
            padding: 20px;
            font-size: 15px;
            color: #f1f5f9;
        }

        QLineEdit {
            background: rgba(15, 23, 42, 0.85);
            border-radius: 14px;
            border: 1px solid rgba(6, 182, 212, 0.15);
            padding: 14px 18px;
            font-size: 15px;
            color: #f8fafc;
        }
        QLineEdit:focus {
            border: 1px solid #06b6d4;
            background: rgba(15, 23, 42, 0.95);
        }

        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06b6d4, stop:1 #0891b2);
            color: #0f172a;
            border-radius: 14px;
            padding: 14px 20px;
            font-weight: bold;
            font-size: 14px;
            border: none;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22d3ee, stop:1 #06b6d4);
        }
        QPushButton:pressed {
            background: #0891b2;
        }

        QListWidget {
            background: rgba(15, 23, 42, 0.5);
            border-radius: 16px;
            border: 1px solid rgba(6, 182, 212, 0.15);
            padding: 10px;
            color: #cbd5e1;
        }
        QListWidget::item {
            padding: 8px;
            border-radius: 8px;
            margin-bottom: 4px;
        }
        QListWidget::item:hover {
            background: rgba(6, 182, 212, 0.1);
        }

        QLabel {
            font-size: 15px;
            font-weight: bold;
            color: #22d3ee;
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
        # Loading indicator (indeterminate progress bar)
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)  # Indeterminate mode
        self.loading_bar.setVisible(False)
        self.loading_bar.setStyleSheet("QProgressBar {border: 2px solid cyan; border-radius: 5px; height: 12px; background: #111827;} QProgressBar::chunk {background-color: cyan;}")
        # Timer label to show elapsed time
        self.timer_label = QLabel("")
        self.timer_label.setStyleSheet("font-size: 12px; color: #88ff88; padding-left: 5px;")
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_timer)
        self.elapsed_seconds = 0

        content_layout.addWidget(self.chat)
        content_layout.addWidget(self.loading_bar)
        content_layout.addWidget(self.timer_label)
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
    def refresh_chat_display(self):
        """Renders the accumulated chat history with beautiful HTML structure and Markdown formatting."""
        html = """
        <style>
            .msg-container { margin-bottom: 20px; font-family: 'Segoe UI', sans-serif; line-height: 1.5; }
            .user-label { color: #d946ef; font-weight: bold; font-size: 13px; margin-bottom: 4px; letter-spacing: 0.5px; }
            .user-body { color: #f8fafc; font-size: 15px; background: rgba(217, 70, 239, 0.06); padding: 12px 16px; border-radius: 12px; border-left: 3px solid #d946ef; }
            .marvis-label { color: #06b6d4; font-weight: bold; font-size: 13px; margin-bottom: 4px; letter-spacing: 0.5px; }
            .marvis-body { color: #f1f5f9; font-size: 15px; background: rgba(6, 182, 212, 0.06); padding: 12px 16px; border-radius: 12px; border-left: 3px solid #06b6d4; }
            .action-body { font-family: Consolas, monospace; background: rgba(16, 185, 129, 0.08); color: #34d399; padding: 12px 16px; border-radius: 8px; border-left: 3px solid #10b981; font-size: 14px; }
            .error-body { font-family: Consolas, monospace; background: rgba(239, 68, 68, 0.08); color: #f87171; padding: 12px 16px; border-radius: 8px; border-left: 3px solid #ef4444; font-size: 14px; }
            code { background: rgba(255, 255, 255, 0.15); padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; font-size: 14px; color: #f43f5e; }
            pre { background: #0f172a; padding: 14px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.08); overflow-x: auto; margin-top: 10px; margin-bottom: 10px; }
            pre code { background: none; padding: 0; color: #e2e8f0; font-size: 13.5px; }
            ul, ol { margin-top: 5px; margin-bottom: 5px; padding-left: 22px; }
            li { margin-bottom: 4px; }
            h1, h2, h3, h4 { color: #22d3ee; margin-top: 15px; margin-bottom: 8px; font-weight: 600; }
            p { margin-top: 0; margin-bottom: 8px; }
            table { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 14px; border-radius: 6px; overflow: hidden; }
            th { background: rgba(6, 182, 212, 0.15); color: #22d3ee; font-weight: bold; border: 1px solid rgba(255, 255, 255, 0.08); padding: 8px 12px; text-align: left; }
            td { border: 1px solid rgba(255, 255, 255, 0.08); padding: 8px 12px; }
            tr:nth-child(even) { background: rgba(255, 255, 255, 0.02); }
        </style>
        """
        for msg in self.chat_messages:
            role = msg["role"]
            content = msg["text"]
            
            if role == "user":
                html += f'<div class="msg-container"><div class="user-label">YOU</div><div class="user-body">{content}</div></div>'
            elif role == "thinking":
                html += f'<div class="msg-container"><div class="marvis-label">MARVIS</div><div class="marvis-body"><span style="color: #06b6d4; font-style: italic;">Thinking...</span></div></div>'
            elif role == "system_action":
                html += f'<div class="msg-container"><div class="action-body">{content}</div></div>'
            elif role == "error":
                html += f'<div class="msg-container"><div class="error-body">{content}</div></div>'
            else:
                rendered_html = MarkdownRenderer.render(content)
                html += f'<div class="msg-container"><div class="marvis-label">MARVIS</div><div class="marvis-body">{rendered_html}</div></div>'
                
        self.chat.setHtml(html)
        
        # Smoothly scroll to the bottom of the chat text area
        cursor = self.chat.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat.setTextCursor(cursor)

    def process(self):
        prompt = self.input.text().strip()
        if not prompt:
            return
        self.input.clear()
        
        # Start loading progress indications
        self.loading_bar.setVisible(True)
        self.timer_label.setVisible(True)
        self.elapsed_seconds = 0
        self.timer.start()
        
        self.chat_messages.append({"role": "user", "text": prompt})
        self.chat_messages.append({"role": "thinking", "text": ""})
        self.refresh_chat_display()
        
        self.run_pipeline(prompt)

    @pyqtSlot(str)
    def handle_voice_input(self, prompt):
        self.reset_mic_button()
        if not prompt or not prompt.strip():
            return
        
        self.chat_messages.append({"role": "user", "text": f"🎙️ {prompt}"})
        self.chat_messages.append({"role": "thinking", "text": ""})
        self.refresh_chat_display()
        
        self.run_pipeline(prompt)

    # ----------------------------------
    # NON-BLOCKING PIPELINE RUNNER
    # ----------------------------------
    def run_pipeline(self, prompt):
        self.is_first_token = True
        self.worker = Worker(self.handle_request, prompt)
        self.worker.token_streamed.connect(self.append_stream_token)
        self.worker.finished.connect(self.completed)
        self.worker.start()

    @pyqtSlot()
    def run_integrations_check(self):
        self.status_label.setText("System Status: Running integration checks...")
        self.chat_messages.append({"role": "system_action", "text": "<b>[Diagnostics]</b> Starting integration check routines..."})
        self.refresh_chat_display()
        self.diagnostic_worker = DiagnosticWorker()
        self.diagnostic_worker.progress.connect(self.handle_integration_progress)
        self.diagnostic_worker.finished.connect(self.handle_integration_finished)
        self.diagnostic_worker.start()

    @pyqtSlot(str, str, str)
    def handle_integration_progress(self, name, status, details):
        self.chat_messages.append({"role": "system_action", "text": f"<b>{name}:</b> {status} - {details}"})
        self.refresh_chat_display()

    @pyqtSlot(dict)
    def handle_integration_finished(self, results):
        report = "<b>Diagnostics Summary Report:</b><br>"
        for name, info in results.items():
            color = "#10b981" if info["status"] == "SUCCESS" else ("#ef4444" if info["status"] == "FAIL" else "#f59e0b")
            report += f"• {name}: <span style='color: {color}; font-weight: bold;'>{info['status']}</span> - {info['details']}<br>"
        self.chat_messages.append({"role": "system_action", "text": report})
        self.refresh_chat_display()
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
        self.chat_messages.append({"role": "system_action", "text": "<b>[Dev Server]</b> Local HTTP Server started listening on http://localhost:8000"})
        self.refresh_chat_display()

    async def handle_request(self, prompt, ui_stream_callback=None):
        result = await Router.detect(prompt)
        return await self.orchestrator.process_request(result, prompt, ui_stream_callback)

    @pyqtSlot(str)
    def append_stream_token(self, token):
        """Fires instantly every single time a character chunk drops from the pipeline."""
        if self.chat_messages and self.chat_messages[-1]["role"] == "thinking":
            self.chat_messages[-1] = {"role": "assistant", "text": ""}
            
        if self.chat_messages and self.chat_messages[-1]["role"] == "assistant":
            self.chat_messages[-1]["text"] += token
            self.refresh_chat_display()

    @pyqtSlot(object)
    def completed(self, result):
        if self.chat_messages and self.chat_messages[-1]["role"] == "thinking":
            self.chat_messages.pop()

        if isinstance(result, dict):
            rtype = result.get("type", "")
            message = result.get("message", "")
            path = result.get("path", "")

            if rtype == "chat":
                if not self.chat_messages or self.chat_messages[-1]["role"] != "assistant":
                    self.chat_messages.append({"role": "assistant", "text": message})
                else:
                    self.chat_messages[-1]["text"] = message
            elif rtype == "automation":
                self.chat_messages.append({"role": "system_action", "text": f"<b>[System Action]</b> {message}"})
            elif path:
                success_msg = f"🎉 **{rtype.upper()} generated successfully!**\n\nFile location path:\n`{path}`"
                self.chat_messages.append({"role": "assistant", "text": success_msg})
                if os.path.exists(path):
                    os.startfile(path)
            else:
                self.chat_messages.append({"role": "assistant", "text": message})
        else:
            if not self.chat_messages or self.chat_messages[-1]["role"] != "assistant":
                self.chat_messages.append({"role": "assistant", "text": str(result)})
            else:
                self.chat_messages[-1]["text"] = str(result)
            
        self.refresh_chat_display()
        self.loading_bar.setVisible(False)
        self.timer.stop()
        self.timer_label.setVisible(False)

    @pyqtSlot(str)
    def update_status_bar(self, status_text):
        self.status_label.setText(f"System Status: {status_text}")
        if "Processing" in status_text or "Error" in status_text:
            self.reset_mic_button()

    @pyqtSlot()
    def update_timer(self):
        """Update the elapsed timer label each second."""
        self.elapsed_seconds += 1
        mins, secs = divmod(self.elapsed_seconds, 60)
        self.timer_label.setText(f"Elapsed: {mins:02d}:{secs:02d}")
        self.reset_mic_button()
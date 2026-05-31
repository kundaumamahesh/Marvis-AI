import asyncio
from PyQt6.QtCore import QThread, pyqtSignal

class Worker(QThread):
    finished = pyqtSignal(object)
    token_streamed = pyqtSignal(str)  # 🔥 Emits every single character/token in real-time

    def __init__(self, coroutine_func, *args, **kwargs):
        """
        Accepts a function reference (*coroutine_func*) and its arguments, 
        allowing safe initialization inside the background thread loop lifecycle.
        """
        super().__init__()
        self.coroutine_func = coroutine_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        # 1. Create a thread-safe callback callback function to send back text tokens
        def stream_callback(token: str):
            self.token_streamed.emit(token)

        # 2. Automatically inject the callback hook into the orchestrator's pipeline arguments
        self.kwargs['ui_stream_callback'] = stream_callback

        # 3. Initialize a dedicated event loop for this background thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Dynamically instantiate the coroutine safely inside its native loop context
            coro = self.coroutine_func(*self.args, **self.kwargs)
            result = loop.run_until_complete(coro)
            self.finished.emit(result)
            
        except Exception as e:
            self.finished.emit({
                "type": "error",
                "status": "error",
                "message": str(e)
            })
        finally:
            loop.close()
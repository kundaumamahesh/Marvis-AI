import subprocess
import os
import sys

class AutomationExecutor:
    # A mapping dictionary of common application names to their system execution command paths
    APP_MAPPING = {
        "notepad": "notepad.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "calculator": "calc.exe",
        "cmd": "cmd.exe",
        "terminal": "cmd.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "task manager": "taskmgr.exe",
        "paint": "mspaint.exe"
    }

    @classmethod
    def open_app(cls, app_name):
        """Attempts to open an application based on string matching."""
        clean_name = app_name.lower().strip()
        
        # 1. Check if the app is inside our quick-launch system registry dictionary
        if clean_name in cls.APP_MAPPING:
            try:
                subprocess.Popen(cls.APP_MAPPING[clean_name])
                return {"type": "automation", "message": f"Opening {app_name} right away."}
            except Exception as e:
                return {"type": "chat", "message": f"Found the shortcut, but failed to run it: {str(e)}"}

        # 2. Advanced Fallback: Search the Windows Start Menu database dynamically
        # This catches apps like Discord, Spotify, Zoom, etc., if installed natively.
        try:
            import winapps
            for app in winapps.search_apps(app_name):
                # If an explicit shortcut path exists, open it directly
                if app.install_location:
                    # Look for executable files inside its folder
                    for root, dirs, files in os.walk(app.install_location):
                        for file in files:
                            if file.lower().endswith(".exe") and app_name.lower() in file.lower():
                                exe_path = os.path.join(root, file)
                                subprocess.Popen(exe_path)
                                return {"type": "automation", "message": f"Successfully launched {app.name}."}
        except ImportError:
            pass # Keep rolling if winapps library isn't installed
        except Exception:
            pass

        # 3. Last Resort: Try passing the raw name straight to the Windows Shell terminal execution layer
        try:
            # shell=True lets Windows look through global environment variables (PATH)
            subprocess.Popen(f"start {clean_name}", shell=True)
            return {"type": "automation", "message": f"Sent a request to Windows to start '{app_name}'."}
        except Exception:
            return {"type": "chat", "message": f"I couldn't locate an application named '{app_name}' on your computer."}
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
        
        # 1. Chrome handling (including YouTube and Google search)
        if clean_name.startswith('chrome'):
            extra = clean_name[len('chrome'):].strip()
            if extra:
                # YouTube handling
                if 'youtube' in extra:
                    from urllib.parse import quote
                    query = extra.replace('youtube', '').strip()
                    if query:
                        search_url = f"https://www.youtube.com/results?search_query={quote(query)}"
                    else:
                        search_url = "https://www.youtube.com"
                    subprocess.Popen(["cmd", "/c", "start", "", "chrome", search_url], shell=True)
                    return {"type": "automation", "message": f"Opening Chrome and navigating to YouTube{' with search' if query else ''}."}
                # General Google search fallback
                from urllib.parse import quote
                search_url = f"https://www.google.com/search?q={quote(extra)}"
                subprocess.Popen(["cmd", "/c", "start", "", "chrome", search_url], shell=True)
                return {"type": "automation", "message": f"Opening Chrome and searching for '{extra}'."}

        # 2. Direct mapping for other known applications (including robust Chrome launch)
        if clean_name in cls.APP_MAPPING:
            # Special handling for Chrome with no extra terms
            if clean_name == "chrome":
                chrome_path = cls._find_executable_in_program_files('chrome')
                if chrome_path:
                    subprocess.Popen([chrome_path])
                    return {"type": "automation", "message": "Opening Chrome from detected installation path."}
                # Fallback to system shell start (uses PATH or registered app)
                try:
                    subprocess.Popen(["cmd", "/c", "start", "", "chrome"], shell=True)
                    return {"type": "automation", "message": "Opening Chrome via system shell."}
                except Exception:
                    return {"type": "chat", "message": "Failed to open Chrome; executable not found."}
            # Default handling for other apps
            try:
                subprocess.Popen(cls.APP_MAPPING[clean_name])
                return {"type": "automation", "message": f"Opening {app_name} via mapping."}
            except Exception:
                pass

        # 3. Dynamic Registry/Database Fallback: Search the Windows Start Menu database (requires winapps)
        try:
            import winapps
            for app in winapps.search_apps(app_name):
                if app.install_location:
                    for root, _, files in os.walk(app.install_location):
                        for file in files:
                            if file.lower().endswith('.exe') and app_name.lower() in file.lower():
                                exe_path = os.path.join(root, file)
                                subprocess.Popen([exe_path])
                                return {"type": "automation", "message": f"Successfully launched {app.name}."}
        except ImportError:
            pass
        except Exception:
            pass

        # 4. Check common installation directories for known apps (e.g., Chrome)
        exe_path = cls._find_executable_in_program_files(clean_name)
        if exe_path:
            try:
                subprocess.Popen([exe_path])
                return {"type": "automation", "message": f"Launched {app_name} from detected path."}
            except Exception as e:
                return {"type": "chat", "message": f"Failed to launch {app_name} from {exe_path}: {str(e)}"}

        # 5. If the user supplied a full filesystem path (file or folder), attempt to open it
        if os.path.exists(app_name):
            try:
                cls.open_path(app_name)
                return {"type": "automation", "message": f"Opened path {app_name}."}
            except Exception as e:
                return {"type": "chat", "message": f"Failed to open path {app_name}: {str(e)}"}

        # 6. Last Resort: Use Windows shell to start the application (handles shortcuts like 'chrome')
        try:
            subprocess.Popen(["cmd", "/c", "start", "", clean_name], shell=True)
            return {"type": "automation", "message": f"Requested Windows to start '{app_name}'."}
        except Exception:
            pass

        # 7. Final fallback – report failure
        return {"type": "chat", "message": f"I couldn't locate an application named '{app_name}' on your computer."}

    @classmethod
    def _find_executable_in_program_files(cls, clean_name):
        """Search common Program Files locations for an executable matching clean_name.
        Returns full path if found, else None."""
        possible_dirs = []
        program_files = os.getenv('PROGRAMFILES')
        program_files_x86 = os.getenv('PROGRAMFILES(X86)')
        if program_files:
            possible_dirs.append(program_files)
        if program_files_x86:
            possible_dirs.append(program_files_x86)
        # Additional typical locations
        possible_dirs.extend([
            os.path.join(os.getenv('LOCALAPPDATA', ''), 'Microsoft', 'WindowsApps'),
            os.path.expanduser('~')
        ])
        for base in possible_dirs:
            if not base:
                continue
            for root, _, files in os.walk(base):
                for file in files:
                    if file.lower().endswith('.exe') and clean_name in file.lower():
                        return os.path.join(root, file)
        return None

    @classmethod
    def open_path(cls, path):
        """Open a file or directory using the default system handler."""
        if os.path.isdir(path):
            subprocess.Popen(['explorer', path])
        else:
            os.startfile(path)

    @classmethod
    def close_app(cls, app_name):
        """Attempts to close or terminate a running application on Windows."""
        clean_name = app_name.lower().strip()
        exe_name = cls.APP_MAPPING.get(clean_name, f"{clean_name}.exe")
        if not exe_name.lower().endswith('.exe'):
            exe_name += ".exe"

        try:
            proc = subprocess.Popen(
                ["taskkill", "/F", "/IM", exe_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            stdout, stderr = proc.communicate()
            
            if proc.returncode == 0:
                return {
                    "type": "automation",
                    "status": "success",
                    "message": f"Successfully closed '{app_name}'."
                }
            else:
                return {
                    "type": "automation",
                    "status": "warning",
                    "message": f"Could not find a running process for '{app_name}' ({exe_name}) to close."
                }
        except Exception as e:
            return {
                "type": "automation",
                "status": "error",
                "message": f"Failed to close application '{app_name}': {str(e)}"
            }

    @classmethod
    def set_system_volume(cls, level):
        """
        Adjusts the absolute system master volume on Windows (0 to 100).
        Uses a lightweight C# keybd_event wrapper via PowerShell.
        """
        try:
            level = max(0, min(100, int(level)))
            ps_code = f"""
            Add-Type -TypeDefinition @"
            using System;
            using System.Runtime.InteropServices;
            public class VolumeControl {{
                [DllImport("user32.dll")]
                public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, uint dwExtraInfo);
                public static void SetVolume(int level) {{
                    for (int i = 0; i < 50; i++) {{
                        keybd_event(0xAE, 0, 0, 0); // Down
                        keybd_event(0xAE, 0, 2, 0); // Release
                    }}
                    int presses = level / 2;
                    for (int i = 0; i < presses; i++) {{
                        keybd_event(0xAF, 0, 0, 0); // Up
                        keybd_event(0xAF, 0, 2, 0); // Release
                    }}
                }}
            }}
            "@
            [VolumeControl]::SetVolume({level})
            """
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            return {
                "type": "automation",
                "status": "success",
                "message": f"System master volume successfully adjusted to {level}%."
            }
        except Exception as e:
            return {
                "type": "automation",
                "status": "error",
                "message": f"Failed to adjust system volume: {str(e)}"
            }
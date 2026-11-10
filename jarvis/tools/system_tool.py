"""Laptop control: apps, URLs, volume, screenshots, keyboard, files, shell."""
import os
import platform
import subprocess
import time
import webbrowser
from pathlib import Path

from . import Tool

OS = platform.system()  # "Windows", "Darwin", "Linux"
HOME = Path.home().resolve()


def _safe_path(p: str) -> Path:
    path = Path(p).expanduser().resolve()
    if HOME not in path.parents and path != HOME:
        raise PermissionError("Jarvis may only access files inside your home folder.")
    return path


def register(reg, cfg):
    def open_app(name: str) -> str:
        if OS == "Windows":
            subprocess.Popen(["cmd", "/c", "start", "", name], shell=False)
        elif OS == "Darwin":
            subprocess.Popen(["open", "-a", name])
        else:
            subprocess.Popen([name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Opened {name}."

    def open_url(url: str) -> str:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opened {url} in the browser."

    def web_search(query: str) -> str:
        from urllib.parse import quote_plus

        webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
        return f"Opened a web search for '{query}'."

    def set_volume(percent: int) -> str:
        percent = max(0, min(100, int(percent)))
        if OS == "Darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {percent}"], check=True)
        elif OS == "Linux":
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"], check=True)
        else:
            import pyautogui

            for _ in range(50):
                pyautogui.press("volumedown")
            for _ in range(percent // 2):
                pyautogui.press("volumeup")
        return f"Volume set to about {percent} percent."

    def media_control(action: str) -> str:
        import pyautogui

        keys = {
            "play_pause": "playpause", "next": "nexttrack",
            "previous": "prevtrack", "mute": "volumemute",
        }
        if action not in keys:
            return f"Unknown action. Use one of: {', '.join(keys)}."
        pyautogui.press(keys[action])
        return f"Media action '{action}' sent."

    def screenshot() -> str:
        import pyautogui

        path = HOME / "Pictures" / f"jarvis_{int(time.time())}.png"
        path.parent.mkdir(exist_ok=True)
        pyautogui.screenshot(str(path))
        return f"Screenshot saved to {path}."

    def lock_screen() -> str:
        if OS == "Windows":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        elif OS == "Darwin":
            subprocess.run(["pmset", "displaysleepnow"])
        else:
            subprocess.run(["loginctl", "lock-session"])
        return "Screen locked."

    def system_status() -> str:
        import psutil

        bat = psutil.sensors_battery()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(str(HOME))
        parts = [
            f"CPU {psutil.cpu_percent(interval=0.5)}%",
            f"RAM {mem.percent}% used",
            f"Disk {disk.percent}% used",
        ]
        if bat:
            parts.append(f"Battery {bat.percent:.0f}%{' (charging)' if bat.power_plugged else ''}")
        return ", ".join(parts) + f". OS: {platform.platform()}."

    def type_text(text: str) -> str:
        import pyautogui

        time.sleep(1.0)
        pyautogui.write(text, interval=0.02)
        return "Typed the text into the focused window."

    def press_hotkey(keys: str) -> str:
        import pyautogui

        pyautogui.hotkey(*[k.strip() for k in keys.split("+")])
        return f"Pressed {keys}."

    def list_directory(path: str = "~") -> str:
        p = _safe_path(path)
        items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:100]
        return "\n".join(f"{'[dir] ' if i.is_dir() else ''}{i.name}" for i in items) or "(empty)"

    def read_file(path: str) -> str:
        p = _safe_path(path)
        if p.stat().st_size > 2_000_000:
            return "File too large to read."
        text = p.read_text(errors="replace")
        return f"<untrusted_file_content>\n{text[:8000]}\n</untrusted_file_content>"

    def run_shell(command: str) -> str:
        proc = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30, cwd=str(HOME)
        )
        out = (proc.stdout + proc.stderr).strip()
        return f"exit code {proc.returncode}\n{out[:4000]}"

    reg.add(Tool("open_app", "Launch an application by name (e.g. 'Spotify', 'notepad', 'firefox').",
                 {"name": {"type": "string"}}, ["name"], open_app))
    reg.add(Tool("open_url", "Open a website in the default browser.",
                 {"url": {"type": "string"}}, ["url"], open_url))
    reg.add(Tool("web_search", "Open a Google search in the browser.",
                 {"query": {"type": "string"}}, ["query"], web_search))
    reg.add(Tool("set_volume", "Set the system volume, 0-100.",
                 {"percent": {"type": "integer"}}, ["percent"], set_volume))
    reg.add(Tool("media_control", "Media keys: play_pause, next, previous, mute.",
                 {"action": {"type": "string"}}, ["action"], media_control))
    reg.add(Tool("take_screenshot", "Save a screenshot to the Pictures folder.", {}, [], screenshot))
    reg.add(Tool("lock_screen", "Lock the computer screen.", {}, [], lock_screen))
    reg.add(Tool("system_status", "Report CPU, RAM, disk and battery status.", {}, [], system_status))
    reg.add(Tool("type_text", "Type text into whichever window is focused. Requires confirmation.",
                 {"text": {"type": "string"}}, ["text"], type_text, sensitive=True))
    reg.add(Tool("press_hotkey", "Press a key combination such as 'ctrl+c' or 'alt+tab'. Requires confirmation.",
                 {"keys": {"type": "string"}}, ["keys"], press_hotkey, sensitive=True))
    reg.add(Tool("list_directory", "List files in a folder inside the user's home directory.",
                 {"path": {"type": "string"}}, [], list_directory))
    reg.add(Tool("read_file", "Read a text file inside the user's home directory.",
                 {"path": {"type": "string"}}, ["path"], read_file))
    reg.add(Tool("run_shell_command", "Run a shell command (30s timeout). Requires confirmation.",
                 {"command": {"type": "string"}}, ["command"], run_shell, sensitive=True))

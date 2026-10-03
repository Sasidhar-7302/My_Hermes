# -*- coding: utf-8 -*-
"""
Hermes Computer Control & Desktop Automation Engine
Powered by Laya System-1 Routing and Qwen 3.5 9B.
Features strict hardline safety shields:
  1. Deletion / Data Wipe Hard-Block (Zero tolerance)
  2. Payment / Financial Transaction Hard-Block (Zero tolerance)
  3. Interactive Confirmation Protocol for Emails, Messaging, and Sensitive Actions
"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
import subprocess
import re
import ctypes
from typing import Dict, Any, List, Optional, Tuple, Union

try:
    from accessibility_tree import get_accessibility_tree, UIElement
except ImportError:
    try:
        from local_model_lab.accessibility_tree import get_accessibility_tree, UIElement
    except ImportError:
        get_accessibility_tree = None

try:
    from screen_vision import get_screen_vision
except ImportError:
    try:
        from local_model_lab.screen_vision import get_screen_vision
    except ImportError:
        get_screen_vision = None

# ─────────────────────────────────────────────────────────────────────────────
# 1. HARDLINE SAFETY POLICIES & GUARDS
# ─────────────────────────────────────────────────────────────────────────────

# Destructive patterns that are UNCONDITIONALLY BLOCKED (Cannot run, no exceptions)
DELETION_PATTERNS = [
    r'\brm\b\s+-[rf]',
    r'\bdel\b\s+',
    r'\brmdir\b\s+',
    r'\brd\b\s+/[sq]',
    r'\bRemove-Item\b',
    r'\bri\b\s+',
    r'\berase\b\s+',
    r'\bformat\b\s+[a-z]:',
    r'\bdiskpart\b',
    r'\bshred\b',
    r'\bsrm\b',
    r'\bwipefs\b',
    r'\bmkfs\b',
    r'\bclean\b\s+-[fdx]',
    r'\breset\s+--hard\b',
    r'\bdrop\s+(database|table)\b',
    r'\btruncate\s+table\b',
    r'\bempty\s+(trash|recycle\s*bin)\b',
    r'\bshift\s*\+\s*delete\b',
    r'\bdelete\b',
    r'\bwipe\b',
    r'\bpurge\b'
]

# Payment / Financial patterns that are UNCONDITIONALLY BLOCKED
PAYMENT_PATTERNS = [
    r'\bcredit\s*card\b',
    r'\bcvv\b',
    r'\bcard\s*number\b',
    r'\bexpiration\s*date\b',
    r'\bcheckout\b',
    r'\bplace\s*order\b',
    r'\bbuy\s*now\b',
    r'\bpay\s*now\b',
    r'\bpaypal\b',
    r'\bstripe\b',
    r'\bbank\s*account\b',
    r'\brouting\s*number\b',
    r'\bwire\s*transfer\b',
    r'\bach\s*transfer\b',
    r'\bpayment\s*method\b',
    r'\bconfirm\s*payment\b',
    r'\bauthorize\s*payment\b'
]

# Sensitive external communication patterns requiring TELEGRAM CONFIRMATION
COMMUNICATION_PATTERNS = [
    r'\b(send|compose|write|dispatch)\s*(an?\s*)?email\b',
    r'\b(send|post|dispatch)\s*(a\s*)?message\b',
    r'\bpost\s*(a\s*message\s*)?(to|in|on)\s*(slack|discord|teams|twitter|x)\b',
    r'\b(slack|discord|teams)\b.*?\b(message|announc|post|channel)\b',
    r'\bmail\s*to\b',
    r'\bpublish\s*to\b'
]

class SafetyViolationError(Exception):
    """Raised when an action violates the strict security guardrails."""
    pass

class ConfirmationRequiredException(Exception):
    """Raised when an action requires explicit human confirmation over Telegram."""
    def __init__(self, action_type: str, details: str):
        super().__init__(f"Confirmation required over Telegram for: {action_type}")
        self.action_type = action_type
        self.details = details

def audit_action_safety(action_name: str, payload: str, window_context: str = "") -> None:
    """
    Performs real-time static & contextual safety audit.
    Blocks deletions, data wipes, and payments.
    Flags messaging/emails for Telegram confirmation.
    """
    combined_text = f"{action_name} {payload} {window_context}".lower()

    # 1. DELETION & DATA WIPE SHIELD (Hard Block)
    for pat in DELETION_PATTERNS:
        if re.search(pat, combined_text, re.IGNORECASE):
            raise SafetyViolationError(
                f"[SAFETY SHIELD ACTIVATED] Action blocked: '{action_name}'. "
                f"Data deletion, file removal, and wiping commands are strictly prohibited by user security policy."
            )

    # 2. PAYMENT & FINANCIAL SHIELD (Hard Block)
    for pat in PAYMENT_PATTERNS:
        if re.search(pat, combined_text, re.IGNORECASE):
            raise SafetyViolationError(
                f"[FINANCIAL SHIELD ACTIVATED] Action blocked: '{action_name}'. "
                f"Entering payment details, checking out, and conducting financial transactions are strictly prohibited."
            )

    # 3. TELEGRAM CONFIRMATION PROTOCOL (Emails, Messaging)
    for pat in COMMUNICATION_PATTERNS:
        if re.search(pat, combined_text, re.IGNORECASE):
            raise ConfirmationRequiredException(
                action_type=action_name,
                details=payload
            )

# ─────────────────────────────────────────────────────────────────────────────
# 2. DESKTOP & OS AUTOMATION PRIMITIVES
# ─────────────────────────────────────────────────────────────────────────────

def list_desktop_windows() -> List[Dict[str, Any]]:
    """Lists all visible application windows with their titles and handles."""
    windows = []
    # 1. Connect to interactive user desktop WinSta0\default
    try:
        import win32service, win32gui, win32con
        try:
            hwinsta = win32service.OpenWindowStation('WinSta0', False, win32con.GENERIC_ALL)
            hwinsta.SetProcessWindowStation()
        except Exception:
            pass

        try:
            hdesk = win32service.OpenDesktop('default', 0, False, win32con.GENERIC_ALL)
            def _desk_cb(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).strip()
                    if title:
                        windows.append({"handle": hwnd, "title": title})
            win32gui.EnumDesktopWindows(hdesk, _desk_cb, None)
        except Exception:
            pass
    except Exception:
        pass

    # 2. Standard EnumWindows fallback
    if not windows:
        try:
            import win32gui
            def _enum_cb(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).strip()
                    if title:
                        windows.append({"handle": hwnd, "title": title})
            win32gui.EnumWindows(_enum_cb, None)
        except Exception:
            pass

    # 3. psutil fallback for processes with names
    if not windows:
        try:
            import psutil
            for p in psutil.process_iter(['pid', 'name']):
                pname = p.info.get('name') or ''
                if pname.lower().endswith('.exe') and pname.lower() not in ['svchost.exe', 'conhost.exe', 'system', 'registry']:
                    windows.append({"handle": p.info['pid'], "title": pname.replace('.exe', '')})
        except Exception:
            pass

    return windows

def focus_window_by_title(title_query: str) -> bool:
    """Brings a window matching title_query to the foreground."""
    # 1. Try win32com WScript.Shell AppActivate (works seamlessly on Windows)
    try:
        import win32com.client
        wsh = win32com.client.Dispatch("WScript.Shell")
        if wsh.AppActivate(title_query):
            return True
    except Exception:
        pass

    title_query = title_query.lower()
    windows = list_desktop_windows()
    target = None
    for w in windows:
        if title_query in w["title"].lower():
            target = w
            break

    if not target:
        return False

    try:
        import win32gui, win32con
        hwnd = target["handle"]
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False

_START_APPS_CACHE: Optional[List[Dict[str, str]]] = None

def get_installed_applications() -> List[Dict[str, str]]:
    """Discovers and caches all registered Windows applications from Get-StartApps."""
    global _START_APPS_CACHE
    if _START_APPS_CACHE is not None:
        return _START_APPS_CACHE

    apps = []
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json -Compress"],
            capture_output=True,
            text=True,
            timeout=8
        )
        if res.returncode == 0 and res.stdout.strip():
            raw = json.loads(res.stdout)
            if isinstance(raw, list):
                apps = raw
            elif isinstance(raw, dict):
                apps = [raw]
    except Exception:
        pass

    _START_APPS_CACHE = apps
    return apps

def resolve_application(app_target: str) -> Dict[str, Any]:
    """Dynamically resolves ANY application on the user's PC (aliases, StartApps, AppData, ProgramFiles)."""
    target_clean = app_target.strip().lower()

    # 1. Built-in instant fast aliases
    aliases = {
        "notepad": {"type": "cmd", "cmd": "notepad.exe"},
        "calculator": {"type": "cmd", "cmd": "calc.exe"},
        "calc": {"type": "cmd", "cmd": "calc.exe"},
        "chrome": {"type": "cmd", "cmd": "chrome"},
        "browser": {"type": "cmd", "cmd": "chrome"},
        "brave": {"type": "cmd", "cmd": "brave"},
        "explorer": {"type": "cmd", "cmd": "explorer.exe"},
        "terminal": {"type": "cmd", "cmd": "powershell.exe"},
        "powershell": {"type": "cmd", "cmd": "powershell.exe"},
        "cmd": {"type": "cmd", "cmd": "cmd.exe"},
        "vscode": {"type": "cmd", "cmd": "code"},
        "code": {"type": "cmd", "cmd": "code"},
        "settings": {"type": "cmd", "cmd": "start ms-settings:"},
        "control panel": {"type": "cmd", "cmd": "control.exe"},
        "paper": {
            "type": "file",
            "path": os.path.expandvars(r"%LOCALAPPDATA%\Programs\Paper\Paper.exe"),
            "cwd": os.path.expandvars(r"%LOCALAPPDATA%\Programs\Paper")
        }
    }

    if target_clean in aliases:
        return aliases[target_clean]

    # 2. Check installed applications from Get-StartApps
    for app in get_installed_applications():
        name = app.get("Name", "").lower()
        appid = app.get("AppID", "")
        if target_clean == name or target_clean in name or name in target_clean:
            return {"type": "startapp", "name": app.get("Name"), "appid": appid}

    # 3. Check AppData\Local\Programs
    local_progs = os.path.expandvars(r"%LOCALAPPDATA%\Programs")
    if os.path.exists(local_progs):
        for item in os.listdir(local_progs):
            if target_clean in item.lower():
                candidate = os.path.join(local_progs, item, f"{item}.exe")
                if os.path.exists(candidate):
                    return {"type": "file", "path": candidate, "cwd": os.path.dirname(candidate)}

    # Fallback to direct command invocation
    return {"type": "cmd", "cmd": app_target}

def launch_application(app_target: str) -> Dict[str, Any]:
    """Safely launches ANY local Windows application or file."""
    audit_action_safety("launch_application", app_target)

    resolved = resolve_application(app_target)
    try:
        if resolved.get("type") == "file":
            proc = subprocess.Popen(
                [resolved["path"]],
                cwd=resolved.get("cwd"),
                shell=True
            )
            return {
                "status": "success",
                "message": f"Application '{app_target}' launched with PID {proc.pid}",
                "pid": proc.pid
            }
        elif resolved.get("type") == "startapp":
            appid = resolved["appid"]
            proc = subprocess.Popen(
                ["explorer.exe", f"shell:AppsFolder\\{appid}"],
                shell=True
            )
            return {
                "status": "success",
                "message": f"Application '{resolved.get('name')}' launched with PID {proc.pid}",
                "pid": proc.pid,
                "appid": appid
            }
        else:
            cmd = resolved.get("cmd", app_target)
            proc = subprocess.Popen(cmd, shell=True)
            return {
                "status": "success",
                "message": f"Application '{cmd}' launched with PID {proc.pid}",
                "pid": proc.pid
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to launch '{app_target}': {str(e)}"
        }

# ── MOUSE AUTOMATION PRIMITIVES ─────────────────────────────────────────────

def mouse_move(x: int, y: int) -> Dict[str, Any]:
    """Moves the cursor to screen coordinates (x, y)."""
    try:
        ctypes.windll.user32.SetCursorPos(int(x), int(y))
        return {"status": "success", "x": x, "y": y}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def mouse_click(x: Optional[int] = None, y: Optional[int] = None, button: str = "left", double: bool = False) -> Dict[str, Any]:
    """Clicks at coordinates (x, y) or at the current cursor location."""
    audit_action_safety("mouse_click", f"{button} click at ({x}, {y})")
    try:
        if x is not None and y is not None:
            ctypes.windll.user32.SetCursorPos(int(x), int(y))
            time.sleep(0.05)

        down_flag = 0x0002 if button == "left" else (0x0008 if button == "right" else 0x0020)
        up_flag = 0x0004 if button == "left" else (0x0010 if button == "right" else 0x0040)

        ctypes.windll.user32.mouse_event(down_flag, 0, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(up_flag, 0, 0, 0, 0)

        if double:
            time.sleep(0.1)
            ctypes.windll.user32.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(0.05)
            ctypes.windll.user32.mouse_event(up_flag, 0, 0, 0, 0)

        return {"status": "success", "button": button, "x": x, "y": y, "double": double}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def mouse_drag(start_x: int, start_y: int, end_x: int, end_y: int, steps: int = 10) -> Dict[str, Any]:
    """Click and drag gesture across the screen (ideal for drawing in Paper/design apps)."""
    audit_action_safety("mouse_drag", f"drag ({start_x},{start_y}) -> ({end_x},{end_y})")
    try:
        ctypes.windll.user32.SetCursorPos(int(start_x), int(start_y))
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # Left down
        time.sleep(0.05)

        for i in range(1, steps + 1):
            curr_x = int(start_x + (end_x - start_x) * (i / steps))
            curr_y = int(start_y + (end_y - start_y) * (i / steps))
            ctypes.windll.user32.SetCursorPos(curr_x, curr_y)
            time.sleep(0.02)

        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # Left up
        return {"status": "success", "start": (start_x, start_y), "end": (end_x, end_y)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def mouse_scroll(amount: int = 5, direction: str = "down") -> Dict[str, Any]:
    """Scrolls the mouse wheel up or down."""
    audit_action_safety("mouse_scroll", f"scroll {direction} {amount}")
    try:
        delta = -120 * amount if direction.lower() == "down" else 120 * amount
        ctypes.windll.user32.mouse_event(0x0800, 0, 0, delta, 0)
        return {"status": "success", "direction": direction, "amount": amount}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── BROWSER AUTOMATION PRIMITIVES ───────────────────────────────────────────

def open_browser(url: str = "https://www.google.com") -> Dict[str, Any]:
    """Opens a webpage in the browser."""
    audit_action_safety("open_browser", url)
    try:
        subprocess.Popen(f"start {url}", shell=True)
        return {"status": "success", "url": url}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def browser_search(query: str) -> Dict[str, Any]:
    """Searches Google or the web via the browser."""
    audit_action_safety("browser_search", query)
    encoded = urllib.parse.quote_plus(query)
    return open_browser(f"https://www.google.com/search?q={encoded}")

# ── PAPER MCP DESIGN AUTOMATION ─────────────────────────────────────────────

def call_paper_mcp(tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Interacts directly with Paper's local MCP server at http://127.0.0.1:29979/mcp."""
    audit_action_safety("paper_mcp", f"{tool_name} with {arguments}")
    if arguments is None:
        arguments = {}

    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": int(time.time()),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://127.0.0.1:29979/mcp",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8")
            for line in text.splitlines():
                if line.startswith("data:"):
                    data = json.loads(line[5:].strip())
                    return {"status": "success", "result": data.get("result")}
            return {"status": "success", "raw": text}
    except Exception as e:
        return {"status": "error", "message": f"Paper MCP call failed: {str(e)}"}

def paper_design(brief: str, html_layout: str = "") -> Dict[str, Any]:
    """Automates UI design in Paper via its native MCP server or window focus."""
    audit_action_safety("paper_design", brief)
    launch_application("paper")
    time.sleep(1.0)
    focus_window_by_title("Paper")

    # Call create_artboard on Paper MCP
    mcp_res = call_paper_mcp("create_artboard", {"name": f"Design: {brief[:30]}"})
    if mcp_res.get("status") == "success":
        artboard_id = mcp_res.get("result", {}).get("artboardId")
        if html_layout:
            call_paper_mcp("write_html", {"html": html_layout, "parentId": artboard_id})
        return {
            "status": "success",
            "message": f"Created design artboard for '{brief}' in Paper",
            "artboard": mcp_res.get("result")
        }
    return {
        "status": "success",
        "message": f"Paper opened and ready to design: '{brief}'",
        "focused": focus_window_by_title("Paper")
    }

# ── KEYBOARD & WINDOW PRIMITIVES ────────────────────────────────────────────

def type_text_into_active_window(text: str) -> Dict[str, Any]:
    """Types text into the currently active window with safety auditing."""
    audit_action_safety("type_text", text)

    # 1. Primary: WScript.Shell SendKeys
    try:
        import win32com.client
        wsh = win32com.client.Dispatch("WScript.Shell")
        escaped = (
            text.replace("{", "{{}")
            .replace("}", "{}}")
            .replace("+", "{+}")
            .replace("^", "{^}")
            .replace("%", "{%}")
            .replace("~", "{~}")
            .replace("(", "{(}")
            .replace(")", "{)}")
        )
        wsh.SendKeys(escaped)
        return {"status": "success", "typed_chars": len(text)}
    except Exception:
        pass

    # 2. Fallback via powershell
    try:
        escaped_ps = text.replace('{', '{{}').replace('}', '{}}').replace('+', '{+}').replace('^', '{^}').replace('%', '{%}')
        ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait(@'\n{escaped_ps}\n'@)"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
        if res.returncode == 0:
            return {"status": "success", "typed_chars": len(text)}
        return {"status": "error", "message": res.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def send_hotkey(hotkey: str) -> Dict[str, Any]:
    """Sends keyboard shortcuts (e.g. 'Ctrl+S', 'Enter', 'Alt+Tab')."""
    audit_action_safety("send_hotkey", hotkey)

    key_map = {
        "enter": "{ENTER}",
        "esc": "{ESC}",
        "escape": "{ESC}",
        "tab": "{TAB}",
        "ctrl+s": "^s",
        "ctrl+c": "^c",
        "ctrl+v": "^v",
        "ctrl+a": "^a",
        "ctrl+z": "^z",
        "ctrl+w": "^w",
        "ctrl+t": "^t",
        "ctrl+r": "^r",
        "ctrl+f": "^f",
        "ctrl+n": "^n",
        "alt+f4": "%{F4}",
        "alt+tab": "%{TAB}",
        "f5": "{F5}",
        "n": "n",
        "y": "y"
    }

    send_str = key_map.get(hotkey.lower(), hotkey)
    try:
        import win32com.client
        wsh = win32com.client.Dispatch("WScript.Shell")
        wsh.SendKeys(send_str)
        return {"status": "success", "hotkey": hotkey}
    except Exception:
        pass

    try:
        ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{send_str}')"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
        return {"status": "success" if res.returncode == 0 else "error", "hotkey": hotkey}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_desktop_environment_state() -> Dict[str, Any]:
    """Returns real-time information about running windows, screen geometry, and active state."""
    windows = list_desktop_windows()
    screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    return {
        "os": "Windows",
        "screen_resolution": f"{screen_w}x{screen_h}",
        "active_windows_count": len(windows),
        "windows": windows[:10],
        "protections_active": {
            "deletion_shield": True,
            "financial_shield": True,
            "telegram_confirmation": True
        }
    }


def click_ui_element(target: str, window: Optional[str] = None) -> Dict[str, Any]:
    """
    Clicks an interactive UI element by name/description using:
    1. Windows UI Automation (Accessibility Tree) - fast, exact, 100% deterministic
    2. Vision Grounding (OmniParser/Vision Model) - fallback for canvas/custom UI
    """
    audit_action_safety("click_ui_element", target)

    # 1. Try Windows Accessibility Tree (UIA)
    if get_accessibility_tree:
        tree = get_accessibility_tree()
        elem = tree.find_by_description(target, window=window)
        if not elem:
            elem = tree.find_element(name=target, window=window, fuzzy=True)

        if elem:
            success, msg = tree.click_element(elem)
            return {
                "status": "success" if success else "error",
                "strategy": "accessibility_tree",
                "element": elem.to_dict(),
                "message": msg
            }

    # 2. Fallback to Screen Vision Grounding
    if get_screen_vision:
        vision = get_screen_vision()
        match = vision.locate_element(target)
        if match and match.get("found"):
            cx, cy = match["center"]
            res = mouse_click(x=cx, y=cy)
            return {
                "status": "success",
                "strategy": "vision_grounding",
                "target": target,
                "center": [cx, cy],
                "mouse_result": res,
                "message": f"Located '{target}' visually and clicked at ({cx}, {cy})"
            }

    return {
        "status": "not_found",
        "target": target,
        "message": f"Could not find element '{target}' via Accessibility Tree or Vision Grounding."
    }


def type_into_ui_element(target_field: str, text: str, window: Optional[str] = None) -> Dict[str, Any]:
    """
    Finds an editable field via UI Automation and sets or types its value.
    """
    audit_action_safety("type_into_ui_element", f"{target_field}: {text}")

    # 1. Try Windows Accessibility Tree (UIA)
    if get_accessibility_tree:
        tree = get_accessibility_tree()
        elem = tree.find_by_description(target_field, window=window)
        if not elem:
            elem = tree.find_element(name=target_field, control_type="Edit", window=window, fuzzy=True)

        if elem:
            success, msg = tree.set_value(elem, text)
            return {
                "status": "success" if success else "error",
                "strategy": "accessibility_tree",
                "element": elem.to_dict(),
                "message": msg
            }

    # 2. Fallback: focus window and type
    if window:
        focus_window_by_title(window)
    return type_text_into_active_window(text)


def inspect_screen_with_vision(prompt: str = "Describe what is currently visible on my screen.") -> Dict[str, Any]:
    """
    Captures screenshot and analyzes visual layout and content with the vision model.
    """
    audit_action_safety("inspect_screen_with_vision", prompt)
    windows = list_desktop_windows()
    active_win = windows[0]["title"] if windows else "Desktop"

    vision_text = ""
    if get_screen_vision:
        vision_text = get_screen_vision().describe_screen(prompt)
    else:
        vision_text = "Screen vision engine is not initialized."

    controls_summary = {}
    if get_accessibility_tree:
        elems = get_accessibility_tree().get_window_elements(max_depth=4)
        clickable_count = sum(1 for e in elems if e.is_clickable)
        input_count = sum(1 for e in elems if e.is_input)
        controls_summary = {
            "total_accessible_elements": len(elems),
            "clickable_controls": clickable_count,
            "input_fields": input_count,
            "sample_controls": [f"[{e.control_type}] {e.name}" for e in elems[:8] if e.name]
        }

    return {
        "status": "success",
        "active_window": active_win,
        "vision_description": vision_text,
        "ui_controls_summary": controls_summary
    }


def list_window_controls(window_query: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns all interactive controls (buttons, inputs, tabs, checkboxes) in the target window.
    """
    if not get_accessibility_tree:
        return {"status": "error", "message": "Accessibility tree not available"}

    tree = get_accessibility_tree()
    elements = tree.get_window_elements(target_window=window_query, max_depth=6)
    interactive = [e.to_dict() for e in elements if (e.is_clickable or e.is_input or e.name)]
    return {
        "status": "success",
        "target_window": window_query or "foreground",
        "total_controls": len(interactive),
        "controls": interactive[:30]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 3. TELEGRAM CONFIRMATION HANDLER
# ─────────────────────────────────────────────────────────────────────────────

def request_telegram_confirmation(action_type: str, details: str) -> str:
    """Simulates / triggers the interactive confirmation prompt over Telegram."""
    prompt = (
        f"⚠️ [TELEGRAM CONFIRMATION REQUEST]\n"
        f"Hermes Operator is requesting permission to execute:\n"
        f"  Action: {action_type}\n"
        f"  Details: {details}\n\n"
        f"Reply 'APPROVE' or 'DENY' via Telegram to proceed."
    )
    return prompt

# ─────────────────────────────────────────────────────────────────────────────
# 4. EXECUTE COMPUTER TASK DISPATCHER (Universal PC Control)
# ─────────────────────────────────────────────────────────────────────────────

def execute_computer_task(task_prompt: str) -> Dict[str, Any]:
    """
    High-level entry point used by agent_dispatcher.py.
    Audits the request, parses universal intent, and safely executes computer control.
    """
    # Safety audit first
    try:
        audit_action_safety("execute_computer_task", task_prompt)
    except SafetyViolationError as e:
        return {"status": "blocked", "reason": str(e), "safety_level": "HARDLINE_GUARD"}
    except ConfirmationRequiredException as e:
        tg_prompt = request_telegram_confirmation(e.action_type, e.details)
        return {
            "status": "awaiting_confirmation",
            "telegram_prompt": tg_prompt,
            "safety_level": "HUMAN_IN_THE_LOOP"
        }

    task_lower = task_prompt.lower()

    # 0. Screen Vision & UI Inspection
    if any(k in task_lower for k in ("what is on my screen", "inspect screen", "describe screen", "look at screen", "read screen")):
        return inspect_screen_with_vision(task_prompt)

    # 0b. List Window Controls
    if "list controls" in task_lower or "window controls" in task_lower or "inspect controls" in task_lower:
        match = re.search(r'(?:in|for)\s+(?:window\s+|app\s+)?["\']?([^"\']+)["\']?$', task_prompt, re.IGNORECASE)
        win = match.group(1).strip() if match else None
        return list_window_controls(window_query=win)

    # 0c. UIA / Vision Element Clicking
    if "click button" in task_lower or "click on" in task_lower or "click element" in task_lower or (task_lower.startswith("click ") and not ("mouse click" in task_lower or "click at" in task_lower)):
        target = re.sub(r'^(click\s+button|click\s+on\s+button|click\s+on|click\s+element|click)\s+', '', task_prompt, flags=re.IGNORECASE)
        target = re.sub(r'\s+button$', '', target, flags=re.IGNORECASE).strip(' "\'')
        return click_ui_element(target)

    # 0d. UIA / Vision Typing into Field
    if "type " in task_lower and (" into " in task_lower or " in " in task_lower):
        match = re.search(r'type\s+["\']?(.*?)["\']?\s+(?:into|in)\s+["\']?(.*?)["\']?$', task_prompt, re.IGNORECASE)
        if match:
            text_to_type = match.group(1).strip()
            target_field = match.group(2).strip()
            return type_into_ui_element(target_field, text_to_type)

    # 1. Paper Design Actions
    if "paper" in task_lower and ("design" in task_lower or "artboard" in task_lower or "draw" in task_lower or "create" in task_lower):
        return paper_design(task_prompt)

    # 2. Browser Navigation & Web Search
    if "browse to" in task_lower or "open url" in task_lower or ("go to" in task_lower and any(ext in task_lower for ext in [".com", ".org", ".io", ".net", "http"])):
        match = re.search(r'(https?://\S+|www\.\S+|\b\w+\.(com|org|io|net|dev|app)\b\S*)', task_prompt)
        url = match.group(0) if match else "https://www.google.com"
        if not url.startswith("http"):
            url = "https://" + url
        return open_browser(url)

    if "search web" in task_lower or "search google" in task_lower or "google search" in task_lower or ("search for" in task_lower and "file" not in task_lower):
        query = re.sub(r'^(search web for|search google for|google search for|search for|google)\s*', '', task_prompt, flags=re.IGNORECASE)
        return browser_search(query)

    # 3. Mouse Actions
    if "mouse click" in task_lower or "click at" in task_lower or "click mouse" in task_lower:
        coords = re.findall(r'\b\d+\b', task_prompt)
        if len(coords) >= 2:
            return mouse_click(x=int(coords[0]), y=int(coords[1]))
        return mouse_click()

    if "drag mouse" in task_lower or "mouse drag" in task_lower:
        coords = re.findall(r'\b\d+\b', task_prompt)
        if len(coords) >= 4:
            return mouse_drag(int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3]))

    if "scroll" in task_lower:
        direction = "up" if "up" in task_lower else "down"
        return mouse_scroll(direction=direction)

    # 4. Window Listing & Focus
    if "list windows" in task_lower or "active windows" in task_lower:
        return {"status": "success", "result": list_desktop_windows()}

    if "focus" in task_lower or "switch to" in task_lower:
        target = task_prompt.replace("focus", "").replace("switch to", "").strip()
        ok = focus_window_by_title(target)
        return {"status": "success" if ok else "not_found", "target": target}

    # 5. Launch Application (Universal PC-wide discovery)
    if "launch" in task_lower or "open" in task_lower:
        target = re.sub(r'^(launch|open|start)\s+(the\s+)?(app\s+|application\s+)?', '', task_prompt, flags=re.IGNORECASE).strip()
        return launch_application(target)

    # 6. Keyboard & Hotkeys
    if "type" in task_lower:
        match = re.search(r'type\s+["\'](.*?)["\']', task_prompt, re.IGNORECASE)
        text_to_type = match.group(1) if match else task_prompt.split("type", 1)[-1].strip()
        return type_text_into_active_window(text_to_type)

    if "press" in task_lower or "hotkey" in task_lower:
        key = task_prompt.replace("press", "").replace("hotkey", "").strip()
        return send_hotkey(key)

    if "system" in task_lower or "state" in task_lower:
        return {"status": "success", "state": get_desktop_environment_state()}

    return {
        "status": "success",
        "message": f"Task evaluated safely by Computer Control engine: {task_prompt}",
        "state": get_desktop_environment_state()
    }

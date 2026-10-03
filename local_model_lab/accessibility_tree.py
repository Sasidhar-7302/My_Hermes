# -*- coding: utf-8 -*-
"""
Accessibility Tree - Windows Native UI Automation Engine for Hermes
Provides deterministic element discovery, inspection, and manipulation using the
Windows UI Automation (UIA) COM interface.

Features:
- Traverses real Windows UI control nodes (Buttons, Inputs, CheckBoxes, Menus, Tabs, Windows)
- Resolves exact bounding boxes and center click coordinates (zero pixel-guessing)
- Fuzzy name matching and AutomationID targeting
- Pattern-based native actions (InvokePattern, TogglePattern, ValuePattern)
- Graceful fallbacks to physical simulated mouse/keyboard actions
- Automatic connection to user interactive desktop WinSta0\\default
"""

from __future__ import annotations

import logging
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Ensure Windows UTF-8 stdout safety
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Check UIA availability
try:
    import uiautomation as auto
    HAS_UIA = True
    auto.TIME_OUT_SECOND = 3
except ImportError:
    HAS_UIA = False
    auto = None
    logger.warning("uiautomation not installed. Run: uv pip install uiautomation")

# Check PyWin32 availability for desktop station attachment
try:
    import win32service, win32gui, win32con, win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


def ensure_interactive_desktop():
    """Ensures process is attached to the user's interactive desktop (WinSta0\\default)."""
    if not HAS_WIN32:
        return
    try:
        hwinsta = win32service.OpenWindowStation('WinSta0', False, win32con.GENERIC_ALL)
        hwinsta.SetProcessWindowStation()
        hdesk = win32service.OpenDesktop('default', 0, False, win32con.GENERIC_ALL)
        hdesk.SetThreadDesktop()
    except Exception:
        pass


@dataclass
class UIElement:
    """Represents a discrete UI element from the Windows Accessibility Tree."""
    name: str
    control_type: str
    automation_id: str
    class_name: str
    bounding_rect: Tuple[int, int, int, int]  # x, y, width, height
    is_enabled: bool
    is_visible: bool
    value: str = ""
    patterns: List[str] = field(default_factory=list)
    hwnd: int = 0
    _native: Any = None

    @property
    def center(self) -> Tuple[int, int]:
        """Calculates exact center coordinate (x, y) for physical clicking."""
        x, y, w, h = self.bounding_rect
        return (x + w // 2, y + h // 2)

    @property
    def is_clickable(self) -> bool:
        """Determines if the element is an interactable clickable control."""
        clickable_types = {
            "Button", "ButtonControl", "CheckBox", "CheckBoxControl",
            "RadioButton", "RadioButtonControl", "MenuItem", "MenuItemControl",
            "ListItem", "ListItemControl", "TreeItem", "TreeItemControl",
            "TabItem", "TabItemControl", "Hyperlink", "HyperlinkControl",
            "SplitButton", "ToolBar", "AppBar"
        }
        return (
            self.control_type in clickable_types
            or "Invoke" in self.patterns
            or "Toggle" in self.patterns
            or "SelectionItem" in self.patterns
        )

    @property
    def is_input(self) -> bool:
        """Determines if the element accepts direct text input."""
        input_types = {
            "Edit", "EditControl", "Document", "DocumentControl",
            "ComboBox", "ComboBoxControl", "Spinner", "SpinnerControl"
        }
        return self.control_type in input_types or "Value" in self.patterns

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "control_type": self.control_type,
            "automation_id": self.automation_id,
            "class_name": self.class_name,
            "bounding_rect": list(self.bounding_rect),
            "center": list(self.center),
            "is_enabled": self.is_enabled,
            "is_visible": self.is_visible,
            "is_clickable": self.is_clickable,
            "is_input": self.is_input,
            "value": self.value,
            "patterns": self.patterns,
        }


class AccessibilityTree:
    """Windows UI Automation Accessibility Tree Manager."""

    def __init__(self):
        self._cache: Dict[str, List[UIElement]] = {}
        self._cache_time: float = 0.0
        self._cache_ttl: float = 2.0

    @property
    def available(self) -> bool:
        return HAS_UIA

    def _control_to_element(self, control, hwnd: int = 0) -> Optional[UIElement]:
        """Converts a native uiautomation Control to a standardized UIElement."""
        if not control:
            return None
        try:
            rect = control.BoundingRectangle
            patterns = []

            # Check common UI Automation patterns
            pattern_map = [
                ("Invoke", auto.PatternId.InvokePattern),
                ("Toggle", auto.PatternId.TogglePattern),
                ("Value", auto.PatternId.ValuePattern),
                ("SelectionItem", auto.PatternId.SelectionItemPattern),
                ("Scroll", auto.PatternId.ScrollPattern),
                ("ExpandCollapse", auto.PatternId.ExpandCollapsePattern),
            ]

            for name, pat_id in pattern_map:
                try:
                    if control.GetPattern(pat_id):
                        patterns.append(name)
                except Exception:
                    pass

            # Extract value if present
            val = ""
            if "Value" in patterns:
                try:
                    val = control.GetValuePattern().Value or ""
                except Exception:
                    pass

            c_type = control.ControlTypeName or ""
            # Normalize e.g. "ButtonControl" -> "Button"
            if c_type.endswith("Control"):
                c_type = c_type[:-7]

            width = rect.width() if hasattr(rect, "width") else (rect.right - rect.left)
            height = rect.height() if hasattr(rect, "height") else (rect.bottom - rect.top)

            return UIElement(
                name=str(control.Name or "").strip(),
                control_type=c_type,
                automation_id=str(control.AutomationId or "").strip(),
                class_name=str(control.ClassName or "").strip(),
                bounding_rect=(rect.left, rect.top, width, height),
                is_enabled=bool(control.IsEnabled),
                is_visible=bool(width > 0 and height > 0 and rect.left > -30000),
                value=val,
                patterns=patterns,
                hwnd=hwnd or getattr(control, "NativeWindowHandle", 0),
                _native=control,
            )
        except Exception as exc:
            logger.debug(f"Failed to convert UIA control: {exc}")
            return None

    def get_top_windows(self) -> List[Dict[str, Any]]:
        """Finds all visible top-level interactive application windows with their HWNDs."""
        ensure_interactive_desktop()
        results = []

        if HAS_WIN32:
            try:
                hdesk = win32service.OpenDesktop('default', 0, False, win32con.GENERIC_ALL)
                def _cb(hwnd, _):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd).strip()
                        if title and len(title) > 1:
                            rect = win32gui.GetWindowRect(hwnd)
                            w = rect[2] - rect[0]
                            h = rect[3] - rect[1]
                            if w > 100 and h > 100 and rect[0] > -30000:
                                results.append({
                                    "hwnd": hwnd,
                                    "title": title,
                                    "rect": (rect[0], rect[1], w, h)
                                })
                win32gui.EnumDesktopWindows(hdesk, _cb, None)
            except Exception:
                pass

        if not results and HAS_WIN32:
            try:
                def _cb(hwnd, _):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd).strip()
                        if title and len(title) > 1:
                            results.append({"hwnd": hwnd, "title": title})
                win32gui.EnumWindows(_cb, None)
            except Exception:
                pass

        return results

    def find_window_by_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Finds the best matching window HWND and title for a natural query."""
        windows = self.get_top_windows()
        q_low = query.lower().strip()

        # 1. Exact or starts-with match
        for w in windows:
            t_low = w["title"].lower()
            if q_low == t_low or t_low.startswith(q_low):
                return w

        # 2. Substring match
        for w in windows:
            t_low = w["title"].lower()
            if q_low in t_low:
                return w

        # 3. Word-level match
        q_words = [w for w in q_low.split() if len(w) > 2]
        if q_words:
            for w in windows:
                t_low = w["title"].lower()
                if any(qw in t_low for qw in q_words):
                    return w

        return windows[0] if windows else None

    def get_window_elements(
        self,
        target_window: Union[int, str, None] = None,
        max_depth: int = 7,
        filter_visible: bool = True,
        filter_types: Optional[List[str]] = None,
    ) -> List[UIElement]:
        """
        Traverses and extracts all UI elements from the specified window or foreground window.
        """
        if not HAS_UIA:
            return []

        ensure_interactive_desktop()
        elements: List[UIElement] = []

        # Resolve target root control
        root_ctrl = None
        target_hwnd = 0

        if isinstance(target_window, int) and target_window > 0:
            target_hwnd = target_window
            try:
                root_ctrl = auto.ControlFromHandle(target_hwnd)
            except Exception as e:
                logger.warning(f"Could not attach to HWND {target_hwnd}: {e}")
        elif isinstance(target_window, str) and target_window.strip():
            w_info = self.find_window_by_query(target_window)
            if w_info:
                target_hwnd = w_info["hwnd"]
                try:
                    root_ctrl = auto.ControlFromHandle(target_hwnd)
                except Exception:
                    pass

        if not root_ctrl:
            try:
                root_ctrl = auto.GetForegroundControl()
            except Exception:
                pass

        if not root_ctrl:
            # Fallback to top window
            windows = self.get_top_windows()
            if windows:
                target_hwnd = windows[0]["hwnd"]
                try:
                    root_ctrl = auto.ControlFromHandle(target_hwnd)
                except Exception:
                    pass

        if not root_ctrl:
            return []

        # Recursive traversal
        visited = set()

        def _traverse(ctrl, depth: int):
            if depth > max_depth or not ctrl:
                return
            try:
                handle = getattr(ctrl, "NativeWindowHandle", 0)
                elem = self._control_to_element(ctrl, hwnd=target_hwnd)
                if elem:
                    include = True
                    if filter_visible and not elem.is_visible:
                        include = False
                    if filter_types and elem.control_type not in filter_types:
                        include = False

                    if include and (elem.name or elem.automation_id or elem.is_clickable or elem.is_input):
                        elements.append(elem)

                for child in ctrl.GetChildren():
                    _traverse(child, depth + 1)
            except Exception as exc:
                logger.debug(f"Traversal step failed: {exc}")

        _traverse(root_ctrl, 0)
        return elements

    def find_element(
        self,
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        automation_id: Optional[str] = None,
        window: Union[int, str, None] = None,
        fuzzy: bool = True,
        visible_only: bool = True,
    ) -> Optional[UIElement]:
        """Finds a single matching UI element."""
        results = self.find_elements(
            name=name,
            control_type=control_type,
            automation_id=automation_id,
            window=window,
            fuzzy=fuzzy,
            visible_only=visible_only,
            max_results=1
        )
        return results[0] if results else None

    def find_elements(
        self,
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        automation_id: Optional[str] = None,
        window: Union[int, str, None] = None,
        fuzzy: bool = True,
        visible_only: bool = True,
        max_results: int = 25,
    ) -> List[UIElement]:
        """Finds all matching UI elements in the target window."""
        types_filter = [control_type] if control_type else None
        all_elements = self.get_window_elements(
            target_window=window,
            filter_visible=visible_only,
            filter_types=types_filter
        )

        matches: List[UIElement] = []
        name_clean = str(name or "").strip().lower()
        id_clean = str(automation_id or "").strip().lower()

        for elem in all_elements:
            if len(matches) >= max_results:
                break

            # 1. Match AutomationID
            if id_clean:
                if id_clean != elem.automation_id.lower():
                    continue

            # 2. Match Control Type
            if control_type:
                c_low = elem.control_type.lower()
                req_low = control_type.lower()
                if req_low not in c_low and c_low not in req_low:
                    continue

            # 3. Match Name
            if name_clean:
                elem_name_low = elem.name.lower()
                elem_id_low = elem.automation_id.lower()

                if not fuzzy:
                    if name_clean != elem_name_low and name_clean != elem_id_low:
                        continue
                else:
                    matched = False
                    if name_clean in elem_name_low or elem_name_low in name_clean:
                        matched = True
                    elif name_clean in elem_id_low:
                        matched = True
                    else:
                        q_words = [w for w in name_clean.split() if len(w) > 2]
                        if q_words and all(qw in elem_name_low or qw in elem_id_low for qw in q_words):
                            matched = True
                    if not matched:
                        continue

            matches.append(elem)

        return matches

    def find_by_description(
        self,
        description: str,
        window: Union[int, str, None] = None
    ) -> Optional[UIElement]:
        """
        Interprets natural language descriptions like:
        - "save button" -> Button named 'Save'
        - "search box" -> Edit control named 'Search'
        - "dark mode toggle" -> CheckBox or Toggle named 'dark mode'
        """
        raw = description.lower().strip()
        type_hints = {
            "button": "Button",
            "btn": "Button",
            "input": "Edit",
            "textbox": "Edit",
            "text field": "Edit",
            "search box": "Edit",
            "search": "Edit",
            "checkbox": "CheckBox",
            "check box": "CheckBox",
            "toggle": "CheckBox",
            "dropdown": "ComboBox",
            "combo": "ComboBox",
            "tab": "TabItem",
            "menu": "MenuItem",
            "link": "Hyperlink",
            "item": "ListItem",
        }

        detected_type = None
        search_name = raw

        for hint, c_type in type_hints.items():
            pattern = rf'\b{re.escape(hint)}\b'
            if re.search(pattern, raw):
                detected_type = c_type
                search_name = re.sub(pattern, "", raw).strip()
                break

        return self.find_element(
            name=search_name if search_name else None,
            control_type=detected_type,
            window=window,
            fuzzy=True
        )

    def click_element(self, element: UIElement) -> Tuple[bool, str]:
        """
        Clicks an element using the best available pattern:
        1. Native InvokePattern (cleanest, doesn't steal mouse)
        2. Native TogglePattern
        3. Native UIA physical click
        4. PyAutoGUI coordinate click fallback
        """
        if not element:
            return False, "Null UIElement provided"

        # 1. Try Invoke Pattern
        if element._native and HAS_UIA:
            try:
                if element._native.GetPattern(auto.PatternId.InvokePattern):
                    element._native.GetInvokePattern().Invoke()
                    return True, f"Invoked '{element.name}' via InvokePattern"
            except Exception as e:
                logger.debug(f"InvokePattern failed: {e}")

        # 2. Try Toggle Pattern
        if element._native and HAS_UIA:
            try:
                if element._native.GetPattern(auto.PatternId.TogglePattern):
                    element._native.GetTogglePattern().Toggle()
                    return True, f"Toggled '{element.name}' via TogglePattern"
            except Exception as e:
                logger.debug(f"TogglePattern failed: {e}")

        # 3. Try Native Control Click
        if element._native and HAS_UIA:
            try:
                element._native.Click(simulateMove=False)
                return True, f"Clicked '{element.name}' via UIA Native Click"
            except Exception as e:
                logger.debug(f"Native click failed: {e}")

        # 4. Fallback: PyAutoGUI coordinate click at center
        try:
            import pyautogui
            cx, cy = element.center
            if cx > 0 and cy > 0:
                pyautogui.click(cx, cy)
                return True, f"Clicked '{element.name}' at coordinates ({cx}, {cy})"
        except Exception as e:
            logger.debug(f"PyAutoGUI click failed: {e}")

        return False, f"Failed all click strategies for '{element.name}'"

    def set_value(self, element: UIElement, text: str) -> Tuple[bool, str]:
        """Sets the text value into an editable UIElement."""
        if not element:
            return False, "Null UIElement provided"

        # 1. Try ValuePattern
        if element._native and HAS_UIA:
            try:
                if element._native.GetPattern(auto.PatternId.ValuePattern):
                    element._native.GetValuePattern().SetValue(text)
                    return True, f"Set value '{text}' via ValuePattern"
            except Exception as e:
                logger.debug(f"ValuePattern failed: {e}")

        # 2. Try SetFocus + SendKeys
        if element._native and HAS_UIA:
            try:
                element._native.SetFocus()
                element._native.SendKeys("{Ctrl}a{Back}")
                element._native.SendKeys(text)
                return True, f"Focused and typed '{text}' into '{element.name}'"
            except Exception as e:
                logger.debug(f"SendKeys failed: {e}")

        # 3. Fallback: PyAutoGUI click + write
        try:
            import pyautogui
            cx, cy = element.center
            pyautogui.click(cx, cy)
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.write(text, interval=0.02)
            return True, f"Clicked ({cx}, {cy}) and typed '{text}' via PyAutoGUI"
        except Exception as e:
            return False, f"Failed to type value: {e}"

    def get_element_tree(
        self,
        window: Union[int, str, None] = None,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """Builds a JSON-serializable hierarchical representation of the active window."""
        elements = self.get_window_elements(target_window=window, max_depth=max_depth)
        return {
            "window": str(window or "active"),
            "total_elements": len(elements),
            "elements": [e.to_dict() for e in elements]
        }


# Global Singleton
_global_tree: Optional[AccessibilityTree] = None


def get_accessibility_tree() -> AccessibilityTree:
    """Returns global singleton AccessibilityTree."""
    global _global_tree
    if _global_tree is None:
        _global_tree = AccessibilityTree()
    return _global_tree

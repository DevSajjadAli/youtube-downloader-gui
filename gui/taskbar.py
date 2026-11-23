"""
Windows Taskbar Integration for YouTube Downloader Pro.
Controls the Windows Taskbar icon's live download progress bar (like Google Chrome),
supports indeterminate pulse (during merging/fetching), error/paused states,
and ensures the custom logo is explicitly bound to the Windows Taskbar button.
"""

import sys
import ctypes
from ctypes import wintypes, c_ulonglong, c_void_p, POINTER, Structure, byref, cast, c_int


# Windows AppUserModelID registration
def set_app_user_model_id(app_id: str = "DevSajjadAli.YouTubeDownloaderPro.Desktop.v2"):
    """Explicitly tell Windows to treat this process as YouTube Downloader Pro,
    so the custom icon appears on the Windows Taskbar instead of the generic Python icon."""
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass


class TaskbarProgress:
    """Manages the Windows 7/10/11 ITaskbarList3 taskbar progress indicator."""

    # TBPFLAG constants
    TBPF_NOPROGRESS    = 0x0
    TBPF_INDETERMINATE = 0x1
    TBPF_NORMAL        = 0x2
    TBPF_ERROR         = 0x4
    TBPF_PAUSED        = 0x8

    def __init__(self, hwnd=None):
        self.hwnd = hwnd
        self._taskbar = None
        self._set_state = None
        self._set_value = None
        if sys.platform == "win32":
            self._init_com()

    def set_hwnd(self, hwnd):
        self.hwnd = hwnd

    def _init_com(self):
        try:
            ole32 = ctypes.windll.ole32
            ole32.CoInitialize(None)

            class GUID(Structure):
                _fields_ = [
                    ('Data1', wintypes.DWORD),
                    ('Data2', wintypes.WORD),
                    ('Data3', wintypes.WORD),
                    ('Data4', wintypes.BYTE * 8)
                ]

            clsid = GUID()
            iid = GUID()
            ole32.CLSIDFromString(ctypes.c_wchar_p('{56FDF344-FD6D-11D0-958A-006097C9A090}'), byref(clsid))
            ole32.CLSIDFromString(ctypes.c_wchar_p('{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}'), byref(iid))

            p = c_void_p()
            hr = ole32.CoCreateInstance(byref(clsid), None, 1, byref(iid), byref(p))
            if hr != 0 or not p.value:
                return

            self._taskbar = p
            vtable = cast(cast(p, POINTER(c_void_p)).contents, POINTER(c_void_p))

            # HrInit is at index 3
            try:
                HrInitProto = ctypes.WINFUNCTYPE(c_int, c_void_p)
                HrInit = HrInitProto(vtable[3])
                HrInit(p)
            except Exception:
                pass

            # SetProgressValue is at index 9: (this, hwnd, ullCompleted, ullTotal)
            SetProgressValueProto = ctypes.WINFUNCTYPE(c_int, c_void_p, wintypes.HWND, c_ulonglong, c_ulonglong)
            self._set_value = SetProgressValueProto(vtable[9])

            # SetProgressState is at index 10: (this, hwnd, tbpFlags)
            SetProgressStateProto = ctypes.WINFUNCTYPE(c_int, c_void_p, wintypes.HWND, c_int)
            self._set_state = SetProgressStateProto(vtable[10])

        except Exception:
            self._taskbar = None

    def set_progress(self, percent: float):
        """Show green progress bar on taskbar icon, exactly like Google Chrome (0 to 100)."""
        if not self._taskbar or not self.hwnd or not self._set_state or not self._set_value:
            return
        try:
            pct = max(0, min(100, int(percent)))
            self._set_state(self._taskbar, self.hwnd, self.TBPF_NORMAL)
            self._set_value(self._taskbar, self.hwnd, pct, 100)
        except Exception:
            pass

    def set_indeterminate(self):
        """Show pulsing/cycling marquee on taskbar icon (e.g. during connection or format merging)."""
        if not self._taskbar or not self.hwnd or not self._set_state:
            return
        try:
            self._set_state(self._taskbar, self.hwnd, self.TBPF_INDETERMINATE)
        except Exception:
            pass

    def set_error(self):
        """Show red error indicator on taskbar icon."""
        if not self._taskbar or not self.hwnd or not self._set_state:
            return
        try:
            self._set_state(self._taskbar, self.hwnd, self.TBPF_ERROR)
        except Exception:
            pass

    def set_paused(self):
        """Show yellow paused indicator on taskbar icon."""
        if not self._taskbar or not self.hwnd or not self._set_state:
            return
        try:
            self._set_state(self._taskbar, self.hwnd, self.TBPF_PAUSED)
        except Exception:
            pass

    def clear(self):
        """Remove taskbar progress bar."""
        if not self._taskbar or not self.hwnd or not self._set_state:
            return
        try:
            self._set_state(self._taskbar, self.hwnd, self.TBPF_NOPROGRESS)
        except Exception:
            pass

"""
Global hotkey polling via GetAsyncKeyState.
Replaces keyboard.add_hotkey(), keyboard.wait(), keyboard.is_pressed().
No kernel driver - pure user-mode polling thread.
"""
import threading
import time
import ctypes
from ctypes import wintypes
from .win_input import _get_vk, VK_MAP, user32

class _HotkeyManager:
    def __init__(self):
        self._callbacks = {}  # vk -> [(key_str, callback), ...]
        self._running = False
        self._thread = None
        self._suppress = {}   # vk -> bool (suppress key after callback fires)
        self._lock = threading.Lock()
        self._suppressed = set()  # vks currently being held down in suppress mode

    def _ensure_running(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()

    def _poll_loop(self):
        """Poll GetAsyncKeyState for registered hotkeys."""
        while self._running:
            with self._lock:
                items = list(self._callbacks.items())
            for vk, entries in items:
                for key_str, cb in entries:
                    if vk in self._suppressed:
                        # Key already held and suppressed
                        continue
                    state = user32.GetAsyncKeyState(vk)
                    if state & 0x8000:  # key is down
                        try:
                            cb()
                        except Exception:
                            pass
                        if self._suppress.get(vk, False):
                            self._suppressed.add(vk)

            # Wait for key release if suppressed
            if self._suppressed:
                still_suppressed = set()
                for vk in self._suppressed:
                    state = user32.GetAsyncKeyState(vk)
                    if not (state & 0x8000):
                        # Key released
                        pass
                    else:
                        still_suppressed.add(vk)
                self._suppressed = still_suppressed

            from utils.misc import wait as _wait
            _wait(0.018, 0.024)  # ~50Hz polling with jitter (anti-cheat: non-perfect timing)

    def add_hotkey(self, key: str, callback, suppress: bool = False):
        vk = _get_vk(key)
        if vk is None:
            raise ValueError(f"Unknown key for hotkey: {key}")
        with self._lock:
            if vk not in self._callbacks:
                self._callbacks[vk] = []
            self._callbacks[vk].append((key, callback))
            self._suppress[vk] = suppress
        self._ensure_running()

    def remove_hotkey(self, key: str, callback=None):
        vk = _get_vk(key)
        if vk is None:
            return
        with self._lock:
            if vk in self._callbacks:
                if callback is None:
                    del self._callbacks[vk]
                else:
                    self._callbacks[vk] = [
                        (k, cb) for k, cb in self._callbacks[vk] if cb != callback
                    ]
                    if not self._callbacks[vk]:
                        del self._callbacks[vk]
                if not any(vk in d for d in [self._callbacks, self._suppress]):
                    self._suppress.pop(vk, None)

    def is_pressed(self, key: str) -> bool:
        vk = _get_vk(key)
        if vk is None:
            return False
        state = user32.GetAsyncKeyState(vk)
        return bool(state & 0x8000)

    def wait(self, key: str = None, suppress: bool = False):
        """Block until the key is pressed. If key is None, wait for any key."""
        if key is not None:
            vk = _get_vk(key)
            if vk is None:
                raise ValueError(f"Unknown key: {key}")
            while True:
                state = user32.GetAsyncKeyState(vk)
                if state & 0x8000:
                    if suppress:
                        while user32.GetAsyncKeyState(vk) & 0x8000:
                            from utils.misc import wait as _wait
                            _wait(0.008, 0.012)
                        return
                from utils.misc import wait as _wait
                _wait(0.018, 0.024)
        else:
            # Wait for any key
            while True:
                for vk in range(1, 256):
                    if user32.GetAsyncKeyState(vk) & 0x8000:
                        return vk
                from utils.misc import wait as _wait
                _wait(0.018, 0.024)

    def hook(self, callback, suppress: bool = False):
        """Register a callback for all key events.
        This is a simplified version - polls all known keys and calls callback.
        Used by gen_ocr_samples.py and node_recorder.py (dev tools only)."""
        def _poll_all():
            while self._running:
                for vk in range(1, 256):
                    state = user32.GetAsyncKeyState(vk)
                    if state & 0x8000:
                        event = {"event_type": "down", "name": None, "scan_code": 0}
                        try:
                            callback(event)
                        except Exception:
                            pass
                        if suppress:
                            while user32.GetAsyncKeyState(vk) & 0x8000:
                                from utils.misc import wait as _wait
                                _wait(0.01, 0.01)
                            break
                from utils.misc import wait as _wait
                _wait(0.02, 0.02)
        self._ensure_running()
        # Run hook in its own thread
        t = threading.Thread(target=_poll_all, daemon=True)
        t.start()

    def pause(self, seconds: float = 0, suppress: bool = False):
        """Pause key processing for a duration. Used by npc_auto_label.py."""
        from utils.misc import wait as _wait
        _wait(seconds, seconds)

# Singleton
_hotkey_manager = _HotkeyManager()

def add_hotkey(key: str, callback, suppress: bool = False):
    _hotkey_manager.add_hotkey(key, callback, suppress=suppress)

def remove_hotkey(key: str, callback=None):
    _hotkey_manager.remove_hotkey(key, callback)

def is_pressed(key: str) -> bool:
    _hotkey_manager._ensure_running()
    return _hotkey_manager.is_pressed(key)

def wait(key: str = None, suppress: bool = False):
    _hotkey_manager._ensure_running()
    return _hotkey_manager.wait(key, suppress=suppress)

def hook(callback, suppress: bool = False):
    return _hotkey_manager.hook(callback, suppress=suppress)

def pause(seconds: float = 0, suppress: bool = False):
    return _hotkey_manager.pause(seconds, suppress)

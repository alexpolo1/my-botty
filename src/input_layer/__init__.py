"""
Native input layer - replaces `keyboard` and `mouse` (pyclick) libraries.
No kernel drivers, no third-party DLLs. Only standard system DLLs (user32, kernel32).

Import as:
    from input_layer import keyboard, mouse

This is a drop-in replacement for the existing `import keyboard` and
`from utils.custom_mouse import mouse` patterns.
"""
from .win_input import (
    _get_vk, key_down, key_up, key_press, send_key, key_state,
    mouse_move, mouse_down, mouse_up, mouse_click, mouse_wheel, get_cursor_pos,
    send_text, VK_MAP
)
from .mouse_impl import mouse

class _Keyboard:
    """
    Drop-in replacement for the `keyboard` library.
    Supports all patterns used in botty: send(), press(), release(), is_pressed(),
    add_hotkey(), wait(), write(), hook(), pause().

    All key presses include stealth micro-pauses and variable press duration
    automatically - no changes to existing code needed.
    """

    def _stealth_before(self):
        """Add micro-pause before key press (stealth)."""
        try:
            from utils.stealth import add_micro_pause
            add_micro_pause()
        except Exception:
            pass

    def _stealth_after(self):
        """Add micro-pause after key press (stealth)."""
        try:
            from utils.stealth import add_micro_pause
            add_micro_pause()
        except Exception:
            pass

    def _stealth_duration(self):
        """Get human-like key press duration."""
        try:
            from utils.stealth import key_press_duration
            return key_press_duration()
        except Exception:
            import random
            return random.uniform(0.02, 0.15)

    def _skill_rotation_hesitation(self):
        """Add hesitation before skill casts (Tier 2 behavior stealth)."""
        try:
            from utils.stealth import skill_rotation_hesitation
            from utils.misc import wait as _wait
            _wait(skill_rotation_hesitation(), skill_rotation_hesitation() * 1.2)
        except Exception:
            import random
            from utils.misc import wait as _wait
            _wait(random.uniform(0.08, 0.3), random.uniform(0.08, 0.3) * 1.2)

    def _maybe_skill_mistake(self, key: str):
        """
        1-2% chance of pressing a random skill key first before the intended one
        (Tier 2 behavior stealth - simulates miscasting).
        Returns True if a mistake was made and corrected.
        """
        try:
            from utils.stealth import should_correct_skill_mistake
            if not should_correct_skill_mistake():
                return False
        except Exception:
            return False

        # Press a random skill key first (simulates miscast)
        import random
        try:
            from config import Config
            skill_keys = list(range(ord('1'), ord('0') + 1))  # Keys 1-0
            wrong_key = chr(random.choice(skill_keys))
            if wrong_key == key:
                wrong_key = chr(random.choice(skill_keys))
        except Exception:
            wrong_key = random.choice(['1', '2', '3', '4', '5'])

        # Send the wrong key
        wrong_vk = _get_vk(wrong_key)
        if wrong_vk is not None:
            key_down(wrong_vk)
            from utils.misc import wait as _wait
            _wait(self._stealth_duration(), self._stealth_duration() * 1.2)
            key_up(wrong_vk)

        return True

    def send(self, key: str, do_press: bool = True, do_release: bool = True, delay=None):
        """
        Send a key press event with stealth timing.

        Supports combo keys like 'shift + a', 'ctrl + alt + del'.
        Supports do_release=False (hold key) and do_press=False (release-only).
        """
        self._stealth_before()

        # Handle combo keys (e.g. 'shift + a', 'ctrl + alt + del')
        if ' + ' in key or '+' in key:
            # Parse combo
            parts = [p.strip() for p in key.replace('+', ' + ').split(' + ') if p.strip()]
            modifiers = []
            final_key = parts[-1]
            for p in parts[:-1]:
                vk = _get_vk(p)
                if vk is not None:
                    modifiers.append(vk)
            vk = _get_vk(final_key)
            if vk is None:
                raise ValueError(f"Unknown key: {key}")
            if do_press:
                for mvk in modifiers:
                    key_down(mvk)
                key_down(vk)
            if do_release:
                if do_press:
                    from utils.misc import wait as _wait
                    _wait(self._stealth_duration(), self._stealth_duration() * 1.2)
                key_up(vk)
                for mvk in reversed(modifiers):
                    key_up(mvk)
            self._stealth_after()
            return

        # Single key
        vk = _get_vk(key)
        if vk is None:
            # Try as a single character
            if len(key) == 1:
                vk = ord(key.upper()) if key.isalpha() else ord(key)
            else:
                raise ValueError(f"Unknown key: {key}")

        if delay is not None:
            from utils.misc import wait as _wait
            _wait(delay, delay * 1.2)

        # Tier 2 stealth: skill hesitation (only for skill hotkeys 1-0)
        if vk in range(ord('1'), ord('0') + 1) or key in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '0'):
            self._skill_rotation_hesitation()
            self._maybe_skill_mistake(key)

        if do_press:
            key_down(vk)
            if do_release:
                from utils.misc import wait as _wait
                _wait(self._stealth_duration(), self._stealth_duration() * 1.2)
        if do_release:
            key_up(vk)

        self._stealth_after()

    def press(self, key: str):
        """Press a key down (without releasing)."""
        self.send(key, do_press=True, do_release=False)

    def release(self, key: str):
        """Release a key (without pressing)."""
        self.send(key, do_press=False, do_release=True)

    def is_pressed(self, key: str) -> bool:
        """Check if a key is currently pressed."""
        vk = _get_vk(key)
        if vk is None:
            return False
        return key_state(key)

    def add_hotkey(self, key: str, callback, suppress: bool = False):
        """Register a global hotkey callback."""
        from .hotkey import add_hotkey as _add_hotkey
        _add_hotkey(key, callback, suppress=suppress)

    def wait(self, key: str = None, suppress: bool = False):
        """Block until the key is pressed. If key is None, wait for any key."""
        from .hotkey import wait as _wait
        return _wait(key, suppress=suppress)

    def write(self, text: str, delay: float = 0.05):
        """Type text character by character."""
        send_text(text, delay=delay)

    def hook(self, callback, suppress: bool = False):
        """Register a callback for all key events (dev tools only)."""
        from .hotkey import hook as _hook
        return _hook(callback, suppress=suppress)

    def pause(self, seconds: float = 0, suppress: bool = False):
        """Pause key processing (used by npc_auto_label.py)."""
        from .hotkey import pause as _pause
        return _pause(seconds, suppress)

# Singleton keyboard object - matches the `keyboard` module API
keyboard = _Keyboard()

# Exports for convenience
__all__ = ["keyboard", "mouse"]

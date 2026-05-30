"""
Log rotation utility for botty screenshot/log directories.

Provides safe_imwrite() — a drop-in replacement for cv2.imwrite() that
automatically rotates old files when a directory exceeds the configured
file count or total size limit.

Usage:
    from utils.log_rotation import safe_imwrite
    safe_imwrite("log/screenshots/pickit/uuid_1.png", img)

Configured via params.ini [log_rotation] section:
    pickit_max_files  = 300       # max files in pickit dir
    pickit_max_mb     = 200       # max MB in pickit dir
    info_max_files    = 100       # max files in info dir
    info_max_mb       = 200       # max MB in info dir
    items_max_files   = 50        # max files in items dir
    items_max_mb      = 50        # max MB in items dir
    discord_notify_rotation = 1   # send Discord message when rotation runs
"""

import os
import time
import cv2
from logger import Logger
from config import Config


# Optional callback set at bot startup: callable(deleted_count, dir_path, total_mb_before)
_rotation_callback = None


def set_rotation_callback(cb):
    """Set a callback that gets called when log rotation deletes files.

    The bot sets this in main.py to send Discord notifications.
    Signature: callback(deleted_count: int, dir_path: str, total_mb_before: float)
    """
    global _rotation_callback
    _rotation_callback = cb


class _DirRotator:
    """Manages file rotation for a single directory."""

    def __init__(self, dir_path: str, max_files: int = 500, max_mb: float = 500):
        self.dir_path = dir_path
        self.max_files = max_files
        self.max_mb = max_mb
        self._last_check = 0
        self._check_interval = 60  # seconds between rotation checks

    def _needs_check(self):
        now = time.time()
        if now - self._last_check < self._check_interval:
            return False
        self._last_check = now
        return True

    def _get_files(self):
        """Return list of (filepath, mtime, size) sorted oldest first."""
        try:
            entries = []
            for fname in os.listdir(self.dir_path):
                fpath = os.path.join(self.dir_path, fname)
                if os.path.isfile(fpath):
                    try:
                        stat = os.stat(fpath)
                        entries.append((fpath, stat.st_mtime, stat.st_size))
                    except OSError:
                        pass
            entries.sort(key=lambda x: x[1])  # oldest first
            return entries
        except OSError:
            return []

    def rotate(self):
        """Delete oldest files until under limits."""
        if not self._needs_check():
            return
        files = self._get_files()
        total_size = sum(f[2] for f in files)
        total_mb = total_size / (1024 * 1024)
        deleted = 0
        for fpath, mtime, fsize in files:
            if len(files) <= self.max_files and total_mb <= self.max_mb:
                break
            try:
                os.remove(fpath)
                total_size -= fsize
                total_mb = total_size / (1024 * 1024)
                deleted += 1
            except OSError:
                pass
        if deleted > 0:
            Logger.debug(f"Log rotation: deleted {deleted} old files from {self.dir_path} "
                         f"(now {total_mb:.0f}MB, {len(files) - deleted} files remaining)")
            # Notify via callback (Discord message)
            if _rotation_callback is not None:
                try:
                    _rotation_callback(deleted, self.dir_path, total_mb)
                except Exception:
                    pass  # never crash the bot over a notification


# Global rotator instances — created on first use, keyed by directory path.
_rotators = {}


def _get_rotator(filepath: str) -> _DirRotator | None:
    """Get or create a rotator for the directory containing filepath.

    Reads limits from Config().log_rotation. Returns None if the
    directory is not managed by log rotation.
    """
    dir_path = os.path.dirname(filepath)
    if dir_path in _rotators:
        return _rotators[dir_path]

    cfg = Config().log_rotation

    # Match directory path to config keys
    if 'pickit' in dir_path:
        max_files = cfg['pickit_max_files']
        max_mb = cfg['pickit_max_mb']
    elif 'info' in dir_path:
        max_files = cfg['info_max_files']
        max_mb = cfg['info_max_mb']
    elif 'items' in dir_path:
        max_files = cfg['items_max_files']
        max_mb = cfg['items_max_mb']
    else:
        return None  # not a managed directory

    rotator = _DirRotator(dir_path, max_files, max_mb)
    _rotators[dir_path] = rotator
    return rotator


def safe_imwrite(filepath: str, img, *args, **kwargs) -> bool:
    """Drop-in replacement for cv2.imwrite() with automatic log rotation.

    Before writing, checks if the parent directory exceeds its file count
    or size limit and rotates old files if needed. Also handles OSError
    gracefully (disk full) without crashing the bot.
    """
    rotator = _get_rotator(filepath)
    if rotator is not None:
        rotator.rotate()

    try:
        return cv2.imwrite(filepath, img, *args, **kwargs)
    except OSError as e:
        Logger.warning(f"safe_imwrite failed for {filepath}: {e}")
        return False
    except Exception as e:
        Logger.warning(f"safe_imwrite unexpected error for {filepath}: {e}")
        return False


def rotate_directory(dir_path: str, max_files: int = 500, max_mb: float = 500):
    """Force-rotate a directory regardless of interval."""
    rotator = _DirRotator(dir_path, max_files, max_mb)
    rotator._last_check = 0  # force check
    rotator.rotate()

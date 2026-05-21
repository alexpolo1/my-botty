from dataclasses import dataclass
from decimal import InvalidOperation
import time
import random
import ctypes
import threading
import logging
import numpy as np
from copy import deepcopy
import unicodedata
import re

from pyparsing import Regex

from logger import Logger
import cv2
import os
from math import cos, sin, dist
import subprocess
import psutil

if os.name == 'nt':
    # Set DPI awareness BEFORE any Win32 GUI calls.
    # Without this, Windows at 80% DPI reports 1280x720 as 1024x576.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor v2
    except:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Per-monitor v1
        except:
            pass

    from win32con import HWND_TOPMOST, SWP_NOMOVE, SWP_NOSIZE, HWND_NOTOPMOST
    from win32gui import GetWindowText, SetWindowPos, EnumWindows, GetClientRect, ClientToScreen
    from win32api import GetMonitorInfo, MonitorFromWindow
    from win32process import GetWindowThreadProcessId
else:
    # Linux stubs — these functions are never called outside os.name == 'nt' blocks,
    # but they must exist for the module to import cleanly on non-Windows systems.
    HWND_TOPMOST = None
    SWP_NOMOVE = None
    SWP_NOSIZE = None
    HWND_NOTOPMOST = None

    def GetWindowText(hwnd):
        return None

    def SetWindowPos(hwnd, flags, x, y, w, h, extra):
        pass

    def EnumWindows(callback, lParam):
        pass

    def GetClientRect(hwnd):
        return (0, 0, 0, 0)

    def ClientToScreen(hwnd, pt):
        return pt

    def GetMonitorInfo(hwnd, info):
        return None

    def MonitorFromWindow(hwnd, flags):
        return None

    def GetWindowThreadProcessId(hwnd):
        return (0, 0)

from rapidfuzz.process import extractOne
try:
    from rapidfuzz.string_metric import levenshtein
except ImportError:
    from rapidfuzz.distance import Levenshtein as levenshtein

def close_down_d2():
    subprocess.call(["taskkill","/F","/IM","D2R.exe"], stderr=subprocess.DEVNULL)

def close_down_bnet_launcher():
    subprocess.call(["taskkill","/F","/IM","Battle.net.exe"], stderr=subprocess.DEVNULL)

@dataclass
class WindowSpec:
    title_regex: 'str | None' = None
    process_name_regex: 'str | None' = None

    def match(self, hwnd) -> bool:
        result = True
        if self.title_regex is not None:
            result = result and Regex(self.title_regex).matches(GetWindowText(hwnd))
        if self.process_name_regex is not None:
            _, process_id = GetWindowThreadProcessId(hwnd)
            if process_id > 0:
                result = result and Regex(self.process_name_regex).matches(psutil.Process(process_id).name())
        if self.title_regex is None and self.process_name_regex is None:
            result = False
        return result

def find_d2r_window(spec: WindowSpec, offset = (0, 0)) -> tuple[int, int]:
    offset_x, offset_y = offset
    if os.name == 'nt':
        window_list = []
        EnumWindows(lambda w, l: l.append(w), window_list)
        for hwnd in window_list:
            if spec.match(hwnd):
                left, top, right, bottom = GetClientRect(hwnd)
                (left, top), (right, bottom) = ClientToScreen(hwnd, (left, top)), ClientToScreen(hwnd, (right, bottom))
                return (left + offset_x, top + offset_y)
    return None

def set_d2r_always_on_top():
    if os.name == 'nt':
        for attempt in range(30):
            windows_list = []
            EnumWindows(lambda w, l: l.append((w, GetWindowText(w))), windows_list)
            found = False
            for w in windows_list:
                if "Diablo II" in w[1]:
                    SetWindowPos(w[0], HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                    print("Set D2R to be always on top")
                    found = True
                    break
            if found:
                return
            wait(0.5, 1.0)
        print('D2R window not found, could not set always on top')
    else:
        print('OS not supported, unable to set D2R always on top')

def restore_d2r_window_visibility():
    if os.name == 'nt':
        windows_list = []
        EnumWindows(lambda w, l: l.append((w, GetWindowText(w))), windows_list)
        for w in windows_list:
            if w[1] == "Diablo II: Resurrected":
                SetWindowPos(w[0], HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                print("Restored D2R window visibility")
    else:
        print('OS not supported, unable to set D2R always on top')

def wait(min_seconds, max_seconds = None):
    if max_seconds is None:
        max_seconds = min_seconds
    base = random.uniform(min_seconds, max_seconds)
    try:
        from config import Config
        cfg = Config().stealth
        # Use Gaussian jitter for more natural-feeling delays
        jitter_min = cfg["wait_jitter_min"]
        jitter_max = cfg["wait_jitter_max"]
        center = (jitter_min + jitter_max) / 2
        sigma = (jitter_max - jitter_min) / 4
        jitter = random.gauss(center, sigma)
        jitter = max(jitter_min * 0.8, min(jitter_max * 1.2, jitter))
    except Exception:
        jitter = 1.0
    time.sleep(base * jitter)
    return

def _force_kill_thread(thread):
    """
    DANGEROUS: Force-kills a thread via CPython private API.
    Only use as a last resort when cooperative shutdown failed.
    Can corrupt locks, cause GIL issues, or corrupt numpy arrays.
    """
    Logger.error(
        f"Force-killing thread '{thread.name}' via PyThreadState_SetAsyncExc. "
        "This is dangerous and can corrupt locks/GIL/numpy arrays!"
    )
    thread_id = thread.ident
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(SystemExit))
    if res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
        Logger.error('Exception raise failure')


def cooperative_shutdown(
    thread,
    bot=None,
    health_manager=None,
    death_manager=None,
    timeout=5.0,
):
    """
    Cooperatively shut down a thread by signalling the owning objects, then join.

    Falls back to _force_kill_thread only if the thread is still alive after
    *timeout* seconds.  This avoids the dangers of PyThreadState_SetAsyncExc
    (corrupted locks, GIL issues, numpy array corruption) in the common path.
    """
    # Signal Bot to stop its run loop
    if bot is not None:
        bot.stop()

    # Signal HealthManager to stop its monitoring loop
    if health_manager is not None:
        health_manager.stop_monitor()

    # Signal DeathManager to stop its monitoring loop
    if death_manager is not None:
        death_manager.stop_monitor()

    # Wait for the thread to finish cooperatively
    thread.join(timeout=timeout)

    if thread.is_alive():
        Logger.warning(
            f"Thread '{thread.name}' did not exit within {timeout}s; "
            "falling back to force kill (PyThreadState_SetAsyncExc)."
        )
        _force_kill_thread(thread)


# Kept for backwards-compatibility so existing imports still work.
# Calls the cooperative path when the owning objects are available;
# otherwise falls back to force kill immediately.
def kill_thread(thread):
    """
    Backwards-compatibility wrapper.
    Prefer cooperative_shutdown() for new code.
    """
    # We can't signal anything without the owning objects, so fall back
    # to force kill.  Callers that own the bot/managers should use
    # cooperative_shutdown() instead.
    _force_kill_thread(thread)

def cut_roi(img, roi):
    x, y, w, h = roi
    return img[y:y+h, x:x+w]

def mask_by_roi(img, roi, type: str = "regular"):
    x, y, w, h = roi
    if type == "regular":
        masked = np.zeros(img.shape, dtype=np.uint8)
        masked[y:y+h, x:x+w] = img[y:y+h, x:x+w]
    elif type == "inverse":
        masked = cv2.rectangle(img, (x, y), (x+w, y+h), (0, 0, 0), -1)
    else:
        return None
    return masked

def is_in_roi(roi: list[float], pos: tuple[float, float]):
    x, y, w, h = roi
    is_in_x_range = x < pos[0] < x + w
    is_in_y_range = y < pos[1] < y + h
    return is_in_x_range and is_in_y_range

def trim_black(image):
    y_nonzero, x_nonzero = np.nonzero(image)
    roi = np.min(x_nonzero), np.min(y_nonzero), np.max(x_nonzero) - np.min(x_nonzero), np.max(y_nonzero) - np.min(y_nonzero)
    img = image[np.min(y_nonzero):np.max(y_nonzero), np.min(x_nonzero):np.max(x_nonzero)]
    return img, roi

def erode_to_black(img: np.ndarray, threshold: int = 14):
    # Cleanup image with erosion image as marker with morphological reconstruction
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)[1]
    kernel = np.ones((3, 3), np.uint8)
    marker = thresh.copy()
    marker[1:-1, 1:-1] = 0
    while True:
        tmp = marker.copy()
        marker = cv2.dilate(marker, kernel)
        marker = cv2.min(thresh, marker)
        difference = cv2.subtract(marker, tmp)
        if cv2.countNonZero(difference) <= 0:
            break
    mask_r = cv2.bitwise_not(marker)
    mask_color_r = cv2.cvtColor(mask_r, cv2.COLOR_GRAY2BGR)
    img = cv2.bitwise_and(img, mask_color_r)
    return img

def roi_center(roi: list[float] = None):
    x, y, w, h = roi
    return round(x + w/2), round(y + h/2)

def color_filter(img, color_range):
    color_ranges=[]
    # ex: [array([ -9, 201,  25]), array([ 9, 237,  61])]
    if color_range[0][0] < 0:
        lower_range = deepcopy(color_range)
        lower_range[0][0] = 0
        color_ranges.append(lower_range)
        upper_range = deepcopy(color_range)
        upper_range[0][0] = 180 + color_range[0][0]
        upper_range[1][0] = 180
        color_ranges.append(upper_range)
    # ex: [array([ 170, 201,  25]), array([ 188, 237,  61])]
    elif color_range[1][0] > 180:
        upper_range = deepcopy(color_range)
        upper_range[1][0] = 180
        color_ranges.append(upper_range)
        lower_range = deepcopy(color_range)
        lower_range[0][0] = 0
        lower_range[1][0] = color_range[1][0] - 180
        color_ranges.append(lower_range)
    else:
        color_ranges.append(color_range)
    color_masks = []
    for color_range in color_ranges:
        hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv_img, color_range[0], color_range[1])
        color_masks.append(mask)
    color_mask = np.bitwise_or.reduce(color_masks) if len(color_masks) > 0 else color_masks[0]
    filtered_img = cv2.bitwise_and(img, img, mask=color_mask)
    return color_mask, filtered_img

def hms(seconds: int):
    seconds = int(seconds)
    h = seconds // 3600
    m = seconds % 3600 // 60
    s = seconds % 3600 % 60
    return '{:02d}:{:02d}:{:02d}'.format(h, m, s)

def load_template(path):
    if os.path.isfile(path):
        try:
            template_img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            return template_img
        except Exception as e:
            print(e)
            raise ValueError(f"Could not load template: {path}")
    else:
        Logger.error(f"Template does not exist: {path}")
    return None

def alpha_to_mask(img: np.ndarray):
    # create a mask from template where alpha == 0
    if img.shape[2] == 4:
        if np.min(img[:, :, 3]) == 0:
            _, mask = cv2.threshold(img[:,:,3], 1, 255, cv2.THRESH_BINARY)
            return mask
    return None

def list_files_in_folder(path: str):
    r = []
    for root, _, files in os.walk(path):
        for name in files:
            r.append(os.path.join(root, name))
    return r

def rotate_vec(vec: np.ndarray, deg: float) -> np.ndarray:
    theta = np.deg2rad(deg)
    rot_matrix = np.array([[cos(theta), -sin(theta)], [sin(theta), cos(theta)]])
    return np.dot(rot_matrix, vec)

def unit_vector(vec: np.ndarray) -> np.ndarray:
    return vec / dist(vec, (0, 0))

def image_is_equal(img1: np.ndarray, img2: np.ndarray) -> bool:
    shape_equal = img1.shape == img2.shape
    if not shape_equal:
        Logger.debug("image_is_equal: Image shape is not equal")
        return False
    return not(np.bitwise_xor(img1, img2).any())

def arc_spread(cast_dir: tuple[float,float], spread_deg: float=10, radius_spread: tuple[float, float] = [.95, 1.05]):
    """
        Given an x,y vec (target), generate a new target that is the same vector but rotated by +/- spread_deg/2
    """
    cast_dir = np.array(cast_dir)
    length = dist(cast_dir, (0, 0))
    adj = (radius_spread[1] - radius_spread[0])*random.random() + radius_spread[0]
    rot = spread_deg*(random.random() - .5)
    return rotate_vec(unit_vector(cast_dir)*(length+adj), rot)


@dataclass
class BestMatchResult:
    match: str
    score: float
    score_normalized: float

def find_best_match(in_str: str, str_list: list[str]) -> BestMatchResult:
    best_match, best_lev, _ = extractOne(in_str, str_list, scorer=levenshtein)
    best_lev_normalized = 1 - best_lev / max(1, len(in_str))
    return BestMatchResult(best_match, best_lev, best_lev_normalized)

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')

def only_lowercase_letters(value):
    if not (x := ''.join(filter( lambda x: x in 'abcdefghijklmnopqrstuvwxyz', value ))):
        x = "botty"
    return x
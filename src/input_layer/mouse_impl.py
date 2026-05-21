"""
Human-like mouse movement with native Windows API.
Replaces custom_mouse.py (which used the `mouse` / pyclick library with mousetool.dll).
Same public API - drop-in replacement.
"""
import math
import random
import time
import threading
import numpy as np
import pytweening

from .win_input import mouse_move as _native_move, mouse_click as _native_click
from .win_input import mouse_down as _native_down, mouse_up as _native_up
from .win_input import get_cursor_pos as _native_get_pos
from .win_input import mouse_wheel as _native_wheel


def isNumeric(val):
    return isinstance(val, (float, int, np.int32, np.int64, np.float32, np.float64))

def isListOfPoints(l):
    if not isinstance(l, list):
        return False
    try:
        isPoint = lambda p: ((len(p) == 2) and isNumeric(p[0]) and isNumeric(p[1]))
        return all(map(isPoint, l))
    except (KeyError, TypeError):
        return False

class BezierCurve():
    @staticmethod
    def binomial(n, k):
        return math.factorial(n) / float(math.factorial(k) * math.factorial(n - k))

    @staticmethod
    def bernsteinPolynomialPoint(x, i, n):
        return BezierCurve.binomial(n, i) * (x ** i) * ((1 - x) ** (n - i))

    @staticmethod
    def bernsteinPolynomial(points):
        def bern(t):
            n = len(points) - 1
            x = y = 0
            for i, point in enumerate(points):
                bern = BezierCurve.bernsteinPolynomialPoint(t, i, n)
                x += point[0] * bern
                y += point[1] * bern
            return x, y
        return bern

    @staticmethod
    def curvePoints(n, points):
        curvePoints = []
        bernstein_polynomial = BezierCurve.bernsteinPolynomial(points)
        for i in range(n):
            t = i / (n - 1)
            curvePoints += bernstein_polynomial(t),
        return curvePoints

class HumanCurve():
    def __init__(self, fromPoint, toPoint, **kwargs):
        self.fromPoint = fromPoint
        self.toPoint = toPoint
        self.points = self.generateCurve(**kwargs)

    def generateCurve(self, **kwargs):
        offsetBoundaryX = kwargs.get("offsetBoundaryX", 100)
        offsetBoundaryY = kwargs.get("offsetBoundaryY", 100)
        leftBoundary = kwargs.get("leftBoundary", min(self.fromPoint[0], self.toPoint[0])) - offsetBoundaryX
        rightBoundary = kwargs.get("rightBoundary", max(self.fromPoint[0], self.toPoint[0])) + offsetBoundaryX
        downBoundary = kwargs.get("downBoundary", min(self.fromPoint[1], self.toPoint[1])) - offsetBoundaryY
        upBoundary = kwargs.get("upBoundary", max(self.fromPoint[1], self.toPoint[1])) + offsetBoundaryY
        knotsCount = kwargs.get("knotsCount", 2)
        distortionMean = kwargs.get("distortionMean", 1)
        distortionStdev = kwargs.get("distortionStdev", 1)
        distortionFrequency = kwargs.get("distortionFrequency", 0.4)
        tween = kwargs.get("tweening", pytweening.easeOutQuad)
        targetPoints = kwargs.get("targetPoints", 10)

        internalKnots = self.generateInternalKnots(leftBoundary, rightBoundary,
            downBoundary, upBoundary, knotsCount)
        points = self.generatePoints(internalKnots)
        points = self.distortPoints(points, distortionMean, distortionStdev, distortionFrequency)
        points = self.tweenPoints(points, tween, targetPoints)
        return points

    def generateInternalKnots(self, leftBoundary, rightBoundary,
        downBoundary, upBoundary, knotsCount):
        if not (isNumeric(leftBoundary) and isNumeric(rightBoundary) and
            isNumeric(downBoundary) and isNumeric(upBoundary)):
            raise ValueError("Boundaries must be numeric")
        if not isinstance(knotsCount, int) or knotsCount < 0:
            raise ValueError("knotsCount must be non-negative integer")
        if leftBoundary > rightBoundary:
            raise ValueError("leftBoundary must be less than or equal to rightBoundary")
        if downBoundary > upBoundary:
            raise ValueError("downBoundary must be less than or equal to upBoundary")

        knotsX = np.random.choice(range(leftBoundary, rightBoundary), size=knotsCount)
        knotsY = np.random.choice(range(downBoundary, upBoundary), size=knotsCount)
        return list(zip(knotsX, knotsY))

    def generatePoints(self, knots):
        if not isListOfPoints(knots):
            raise ValueError("knots must be valid list of points")
        midPtsCnt = max(
            abs(self.fromPoint[0] - self.toPoint[0]),
            abs(self.fromPoint[1] - self.toPoint[1]),
            2)
        knots = [self.fromPoint] + knots + [self.toPoint]
        return BezierCurve.curvePoints(midPtsCnt, knots)

    def distortPoints(self, points, distortionMean, distortionStdev, distortionFrequency):
        if not (isNumeric(distortionMean) and isNumeric(distortionStdev) and
               isNumeric(distortionFrequency)):
            raise ValueError("Distortions must be numeric")
        if not isListOfPoints(points):
            raise ValueError("points must be valid list of points")
        if not (0 <= distortionFrequency <= 1):
            raise ValueError("distortionFrequency must be in range [0,1]")

        distorted = []
        for i in range(1, len(points) - 1):
            x, y = points[i]
            delta = np.random.normal(distortionMean, distortionStdev) if \
                random.random() < distortionFrequency else 0
            distorted += (x, y + delta),
        distorted = [points[0]] + distorted + [points[-1]]
        return distorted

    def tweenPoints(self, points, tween, targetPoints):
        if not isListOfPoints(points):
            raise ValueError("points must be valid list of points")
        if not isinstance(targetPoints, int) or targetPoints < 2:
            raise ValueError("targetPoints must be an integer greater or equal to 2")
        res = []
        for i in range(targetPoints):
            index = int(tween(float(i) / (targetPoints - 1)) * (len(points) - 1))
            res += points[index],
        return res


class mouse:
    """
    Drop-in replacement for the `mouse` (pyclick) library.
    Same public API as custom_mouse.py, but uses native SendInput instead of mousetool.dll.
    """

    @staticmethod
    def sleep(duration):
        from utils.misc import wait as _wait
        _wait(duration, duration * 1.2)

    @staticmethod
    def move(x, y, absolute: bool = True, randomize: int | tuple[int, int] = 5,
             delay_factor: tuple[float, float] = [0.4, 0.6]):
        from_point = _native_get_pos()
        dist = math.dist((x, y), from_point)
        offsetBoundaryX = max(10, int(0.08 * dist))
        offsetBoundaryY = max(10, int(0.08 * dist))
        targetPoints = min(6, max(3, int(0.004 * dist)))
        if not absolute:
            x = from_point[0] + x
            y = from_point[1] + y

        if type(randomize) is int:
            randomize = int(randomize)
            if randomize > 0:
                x = int(x) + random.randrange(-randomize, +randomize)
                y = int(y) + random.randrange(-randomize, +randomize)
        else:
            randomize = (int(randomize[0]), int(randomize[1]))
            if randomize[1] > 0 and randomize[0] > 0:
                x = int(x) + random.randrange(-randomize[0], +randomize[0])
                y = int(y) + random.randrange(-randomize[1], +randomize[1])

        # Apply human curve complexity from stealth config
        try:
            from config import Config
            complexity = Config().stealth.get("human_curve_complexity", 1.0)
        except Exception:
            complexity = 1.0

        distortionMean = 1 * complexity
        distortionStdev = 1 * complexity
        distortionFreq = min(0.8, 0.4 * complexity)

        human_curve = HumanCurve(
            from_point, (x, y),
            offsetBoundaryX=offsetBoundaryX,
            offsetBoundaryY=offsetBoundaryY,
            targetPoints=targetPoints,
            distortionMean=distortionMean,
            distortionStdev=distortionStdev,
            distortionFrequency=distortionFreq
        )

        duration = min(0.5, max(0.05, dist * 0.0004) * random.uniform(delay_factor[0], delay_factor[1]))
        delta = duration / len(human_curve.points)

        for point in human_curve.points:
            _native_move(int(point[0]), int(point[1]))
            mouse.sleep(delta)

    @staticmethod
    def stealth_move(x, y, absolute: bool = True, randomize: int | tuple[int, int] = 5,
                     delay_factor: tuple[float, float] = [0.4, 0.6]):
        """Move with full stealth chain: pre-movement pause -> randomized position -> endpoint wobble."""
        try:
            from utils.stealth import randomize_click_position, add_micro_pause, endpoint_wobble
            rx, ry = randomize_click_position(x, y)
            add_micro_pause()
        except Exception:
            from logger import Logger
            Logger.warning("[Stealth] randomize_click_position/add_micro_pause failed, using manual fallback")
            try:
                from config import Config
                variance = Config().stealth["click_variance"]
            except Exception:
                variance = 0
            rx = x + random.randint(-variance, variance)
            ry = y + random.randint(-variance, variance)
        mouse.move(rx, ry, absolute=absolute, randomize=5 + variance, delay_factor=delay_factor)
        try:
            from utils.stealth import endpoint_wobble
            wx, wy = endpoint_wobble(rx, ry)
            _native_move(wx, wy)
        except Exception:
            from logger import Logger
            Logger.warning("[Stealth] endpoint_wobble failed, skipping micro-adjustment")
            pass

    @staticmethod
    def _is_clicking_safe():
        try:
            import screen
            from config import Config
            from utils.misc import is_in_roi
            import template_finder
            mouse_pos = screen.convert_monitor_to_screen(_native_get_pos())
            is_inventory_open = template_finder.search(
                "INVENTORY_GOLD_BTN",
                screen.grab(),
                threshold=0.8,
                roi=Config().ui_roi["gold_btn"],
                use_grayscale=True
            ).valid
            if is_inventory_open:
                is_in_equipped_area = is_in_roi(Config().ui_roi["equipped_inventory_area"], mouse_pos)
                is_in_restricted_inventory_area = is_in_roi(Config().ui_roi["restricted_inventory_area"], mouse_pos)
                if is_in_restricted_inventory_area or is_in_equipped_area:
                    from logger import Logger
                    Logger.error("Mouse wants to click in equipped area. Cancel action.")
                    return False
        except Exception:
            pass
        return True

    @staticmethod
    def click(button):
        if button != "left" or mouse._is_clicking_safe():
            try:
                from utils.stealth import apply_click_delay
                apply_click_delay()
            except Exception:
                from logger import Logger
                Logger.warning("[Stealth] apply_click_delay failed, falling back to manual delay")
                from utils.misc import wait as _wait
                _wait(0.05, 0.3)
            _native_click(button)

    @staticmethod
    def press(button):
        if button != "left" or mouse._is_clicking_safe():
            _native_down(button)

    @staticmethod
    def release(button):
        _native_up(button)

    @staticmethod
    def get_position():
        return _native_get_pos()

    @staticmethod
    def wheel(delta):
        _native_wheel(delta)

    @staticmethod
    def async_move(x, y, absolute=True, randomize=5, delay_factor=[0.4, 0.6]):
        result = {"_done": False, "_lock": threading.Lock()}

        def _run():
            try:
                mouse.move(x, y, absolute=absolute, randomize=randomize, delay_factor=delay_factor)
            finally:
                with result["_lock"]:
                    result["_done"] = True

        threading.Thread(target=_run, daemon=True).start()

        def done():
            with result["_lock"]:
                return result["_done"]

        def wait(timeout=None):
            deadline = None if timeout is None else time.monotonic() + timeout
            while not done():
                if deadline is not None and time.monotonic() >= deadline:
                    return False
                from utils.misc import wait as _wait
                _wait(0.01, 0.012)
            return True

        return {"done": done, "wait": wait}


if __name__ == "__main__":
    print("Mouse module loaded OK (native SendInput, no mousetool.dll)")
    pos = mouse.get_position()
    print(f"Cursor at: {pos}")

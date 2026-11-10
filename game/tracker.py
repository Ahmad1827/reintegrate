"""Webcam hand tracking turned into game controls. Runs on its own thread.

Controls it produces:
  move  - hand left / right of the middle of the picture (analog, -1..1)
  jump  - hand raised into the top of the picture, or a quick upward flick
  fist  - closed hand (crouch / hold still)
"""
import math
import os
import sys
import threading
import time

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/1/hand_landmarker.task")

DEAD = 0.07      # half-width of the neutral zone around the centre
SPAN = 0.17      # distance past the neutral zone that means full speed
JUMP_ON = 0.36   # hand centre above this line (0 = top of picture) -> jump
JUMP_OFF = 0.43

CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10),
               (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18),
               (18, 19), (19, 20), (0, 17)]


def _model_bytes():
    folder = os.path.join(os.path.expanduser("~"), ".reintegrate")
    path = os.path.join(folder, "hand_landmarker.task")
    if not os.path.exists(path):
        import urllib.request
        os.makedirs(folder, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, path + ".part")
        os.replace(path + ".part", path)
    with open(path, "rb") as f:
        return f.read()


def make_detector(mp):
    """Return f(rgb_image) -> list of 21 (x, y) or None. Works with old and new MediaPipe."""
    if hasattr(mp, "solutions") and hasattr(mp.solutions, "hands"):
        hands = mp.solutions.hands.Hands(max_num_hands=1, model_complexity=0,
                                         min_detection_confidence=0.6,
                                         min_tracking_confidence=0.5)

        def detect(rgb):
            res = hands.process(rgb)
            if not res.multi_hand_landmarks:
                return None
            return [(p.x, p.y) for p in res.multi_hand_landmarks[0].landmark]
        return detect

    from mediapipe.tasks import python as mpp
    from mediapipe.tasks.python import vision
    opts = vision.HandLandmarkerOptions(
        base_options=mpp.BaseOptions(model_asset_buffer=_model_bytes()), num_hands=1)
    landmarker = vision.HandLandmarker.create_from_options(opts)

    def detect(rgb):
        res = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        if not res.hand_landmarks:
            return None
        return [(p.x, p.y) for p in res.hand_landmarks[0]]
    return detect


class HandTracker:
    def __init__(self):
        self.status = "off"          # off | starting | ready | error
        self.message = "camera off"
        self.present = False
        self.move = 0.0
        self.jump = False
        self.fist = False
        self.x = 0.5
        self.y = 0.5
        self.points = []
        self._stop = False
        self._thread = None
        self._seen = 0.0
        self._last = None
        self._flick = 0.0
        self._fist_n = 0

    def start(self):
        if self._thread and self._thread.is_alive():
            if not self._stop:
                return
            self._thread.join(2.0)
        self._stop = False
        self.status = "starting"
        self.message = "starting camera..."
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True
        self.present = False
        self.move, self.jump, self.fist = 0.0, False, False
        if self.status != "error":
            self.status, self.message = "off", "camera off"

    def _fail(self, msg):
        self.status, self.message, self.present = "error", msg, False
        self.move, self.jump, self.fist = 0.0, False, False

    def _run(self):
        try:
            import cv2
            import mediapipe as mp
        except Exception:
            return self._fail("hand tracking not installed - keyboard only")
        try:
            detect = make_detector(mp)
        except Exception as e:
            return self._fail("hand tracking failed to load (%s)" % type(e).__name__)
        cap = None
        try:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) if sys.platform == "win32" else cv2.VideoCapture(0)
            if not cap or not cap.isOpened():
                return self._fail("no camera found - keyboard only")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.status, self.message = "ready", "camera on - show your hand"
            misses = 0
            while not self._stop:
                ok, frame = cap.read()
                if not ok:
                    misses += 1
                    if misses > 80:
                        return self._fail("camera stopped responding - keyboard only")
                    time.sleep(0.03)
                    continue
                misses = 0
                rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
                self.feed(detect(rgb))
        except Exception as e:
            self._fail("camera error (%s) - keyboard only" % type(e).__name__)
        finally:
            if cap is not None:
                cap.release()

    def feed(self, pts, now=None):
        """Turn one frame of landmarks (or None) into control state."""
        now = time.time() if now is None else now
        if not pts:
            if now - self._seen > 0.4:
                self.present = False
                self.move, self.jump, self.fist = 0.0, False, False
                self._last = None
            return
        self._seen = now
        self.points = pts
        cx, cy = pts[9]
        if not self.present:
            self.x, self.y = cx, cy
        self.x += (cx - self.x) * 0.5
        self.y += (cy - self.y) * 0.5
        self.present = True

        def dist(a, b):
            return math.hypot(pts[a][0] - pts[b][0], pts[a][1] - pts[b][1])

        curled = sum(1 for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18))
                     if dist(tip, 0) < dist(pip, 0) * 1.08)
        self._fist_n = min(4, self._fist_n + 1) if curled >= 3 else max(0, self._fist_n - 1)
        if self._fist_n >= 3:
            self.fist = True
        elif self._fist_n <= 1:
            self.fist = False

        d = self.x - 0.5
        self.move = 0.0 if abs(d) < DEAD else math.copysign(min(1.0, (abs(d) - DEAD) / SPAN), d)

        if self._last:
            ly, lt = self._last
            if now > lt and (cy - ly) / (now - lt) < -1.7:
                self._flick = now + 0.22
        self._last = (cy, now)
        zone = self.y < (JUMP_OFF if self.jump else JUMP_ON)
        self.jump = (zone or now < self._flick) and not self.fist

"""
car_ai.py  -  obstacle detection + decision, runs on the PC.

Video comes from the ESP32-CAM (--ip), commands go to the MOTOR ESP32 (--motor-ip)
using the same URLs as the manual controller:
    /action=FORWARD  /action=BACKWARD  /action=LEFT  /action=RIGHT  /action=STOP

Internal commands: F, B, L, R, S.
By default nothing is sent to the car (display only). Add --send to drive.
"""
import argparse, collections, glob, os, threading, time
import cv2, numpy as np, requests
from ultralytics import YOLO
from stream_reader import LatestFrame

# ================= SETTINGS =================
TARGET_ID    = 0      # ArUco marker ID placed at point B
ARRIVED_AREA = 0.06   # marker fraction of the frame at which we stop
OBSTACLE_THR = 0.10   # fraction of the centre zone covered by objects = blocked
CONF         = 0.40   # YOLO confidence
ROI_TOP      = 0.35   # ignore the upper part of the image
SEARCH_TURN  = "F"    # turn direction when the target is not visible
SMOOTH_N     = 3      # majority vote over the last N decisions (stops are never delayed)
SIZE         = (320, 240)   # same size as the ESP32-CAM stream
# ============================================

ACTIONS = {"F": "FORWARD", "B": "BACKWARD", "L": "LEFT", "R": "RIGHT", "S": "STOP"}

model = YOLO("yolov8n.pt")
aruco = cv2.aruco
detector = aruco.ArucoDetector(aruco.getPredefinedDictionary(aruco.DICT_4X4_50),
                               aruco.DetectorParameters())


# ---------------- sources ----------------
class FileSource:
    """Video file or folder of images, resized to the ESP32-CAM resolution."""
    def __init__(self, path):
        self.finished, self.idx, self.cap, self.files = False, 0, None, []
        if os.path.isdir(path):
            self.files = sorted(glob.glob(os.path.join(path, "*.jpg")) +
                                glob.glob(os.path.join(path, "*.png")))
        else:
            self.cap = cv2.VideoCapture(path)

    def get(self):
        frame = None
        if self.cap is not None:
            ok, frame = self.cap.read()
            if not ok:
                frame = None
        elif self.idx < len(self.files):
            frame = cv2.imread(self.files[self.idx])
        if frame is None:
            self.finished = True
            return None, self.idx
        self.idx += 1
        return cv2.resize(frame, SIZE), self.idx

    def stop(self):
        pass


# ---------------- link to the motor ESP32 ----------------
class MotorLink(threading.Thread):
    """Sends the latest command to the motor ESP32 every 120 ms (heartbeat).
    The motor ESP32 stops by itself if the heartbeat stops (500 ms)."""
    def __init__(self, ip, speed=None):
        super().__init__(daemon=True)
        self.base = f"http://{ip}"
        self.speed = speed
        self.cmd = "S"
        self.running = True
        self.lock = threading.Lock()
        self.session = requests.Session()

    def set(self, cmd):
        with self.lock:
            self.cmd = cmd

    def run(self):
        if self.speed is not None:
            try:
                self.session.get(f"{self.base}/speed={int(self.speed)}", timeout=1.0)
            except requests.RequestException:
                print("Could not set the speed (is the motor ESP32 reachable?)")
        while self.running:
            with self.lock:
                cmd = self.cmd
            try:
                self.session.get(f"{self.base}/action={ACTIONS[cmd]}&ai=1", timeout=0.5)
            except requests.RequestException:
                pass
            time.sleep(0.12)
        try:
            self.session.get(f"{self.base}/action=STOP&ai=1", timeout=0.5)
        except requests.RequestException:
            pass

    def stop(self):
        self.running = False
        self.join(timeout=1.5)


# ---------------- vision ----------------
def zone_scores(frame, results):
    """Fraction of each zone (left, centre, right) covered by detected objects."""
    h, w = frame.shape[:2]
    y0 = int(h * ROI_TOP)
    zones = [(0, w // 3), (w // 3, 2 * w // 3), (2 * w // 3, w)]
    scores = [0.0, 0.0, 0.0]
    for box in results[0].boxes:
        if float(box.conf[0]) < CONF:
            continue
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        y1 = max(y1, y0)
        if y2 <= y1:
            continue
        for i, (zx1, zx2) in enumerate(zones):
            ox = max(0, min(x2, zx2) - max(x1, zx1))
            scores[i] += (ox * (y2 - y1)) / float((zx2 - zx1) * (h - y0))
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
    return scores


def find_target(frame):
    """Returns (cx_fraction, area_fraction) of the target marker, or None."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = detector.detectMarkers(gray)
    if ids is None:
        return None
    h, w = frame.shape[:2]
    for c, i in zip(corners, ids.flatten()):
        if int(i) == TARGET_ID:
            pts = c.reshape(-1, 2)
            area = cv2.contourArea(pts.astype(np.float32)) / float(w * h)
            cv2.polylines(frame, [pts.astype(int)], True, (0, 255, 0), 2)
            return pts[:, 0].mean() / w, area
    return None


def decide(frame, results):
    """
    >>> THIS IS THE FUNCTION THE TEAM IMPROVES <<<
    Input : frame (BGR 320x240), YOLO results
    Output: (command, state_text, zone_scores)   command is one of F, L, R, S
    """
    scores = zone_scores(frame, results)
    left, centre, right = scores
    target = find_target(frame)

    if target and target[1] > ARRIVED_AREA:
        return "S", "ARRIVED", scores
    if centre > OBSTACLE_THR:
        if left > OBSTACLE_THR and right > OBSTACLE_THR:
            return "S", "BLOCKED", scores
        return ("L" if left < right else "R"), "AVOID", scores
    if target:
        cx = target[0]
        if cx < 0.40:
            return "L", "ALIGN", scores
        if cx > 0.60:
            return "R", "ALIGN", scores
        return "F", "GO", scores
    return SEARCH_TURN, "SEARCH", scores


history = collections.deque(maxlen=SMOOTH_N)


def smooth(cmd):
    """Majority vote to stop L/R flickering. A STOP is applied immediately."""
    if cmd == "S":
        history.clear()
        return "S"
    history.append(cmd)
    return collections.Counter(history).most_common(1)[0][0]


# ---------------- main ----------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="stream",
                   help="'stream' (live ESP32-CAM), a video file, or a folder of images")
    p.add_argument("--ip", help="ESP32-CAM IP (needed for --source stream)")
    p.add_argument("--motor-ip", help="MOTOR ESP32 IP (needed with --send)")
    p.add_argument("--send", action="store_true", help="really drive the car (default: only display)")
    p.add_argument("--speed", type=int, default=None, help="motor speed 0-255 (sent once at start)")
    p.add_argument("--delay", type=float, default=0.2, help="seconds per frame when replaying files")
    a = p.parse_args()

    if a.source == "stream":
        if not a.ip:
            p.error("--ip (ESP32-CAM) is required for the live stream")
        src = LatestFrame(f"http://{a.ip}:81/stream")
        src.start()
    else:
        src = FileSource(a.source)

    link = None
    if a.send:
        if not a.motor_ip:
            p.error("--motor-ip is required with --send")
        link = MotorLink(a.motor_ip, a.speed)
        link.start()

    running, paused = False, False
    print("Keys: g = go (only with --send)   s = stop   space = pause   q = quit")

    while True:
        if not paused:
            frame, _ = src.get()
            if frame is None:
                if getattr(src, "finished", False):
                    break
                time.sleep(0.05)
                continue

            results = model.predict(frame, imgsz=320, conf=CONF, verbose=False)
            raw_cmd, state, scores = decide(frame, results)
            cmd = smooth(raw_cmd)
            if state == "ARRIVED":
                running = False

            final = cmd if (running and link) else "S"
            if link:
                link.set(final)

            h, w = frame.shape[:2]
            cv2.line(frame, (w // 3, 0), (w // 3, h), (255, 255, 0), 1)
            cv2.line(frame, (2 * w // 3, 0), (2 * w // 3, h), (255, 255, 0), 1)
            shown = final if link else cmd
            cv2.putText(frame, f"{state}  cmd={shown}  run={running}", (5, 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(frame, "L:%.2f C:%.2f R:%.2f" % tuple(scores), (5, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.imshow("car", cv2.resize(frame, None, fx=2, fy=2))

        k = cv2.waitKey(1 if a.source == "stream" else max(1, int(a.delay * 1000))) & 0xFF
        if k == ord("g") and link:
            running = True
        elif k == ord("s"):
            running = False
            if link:
                link.set("S")
        elif k == ord(" "):
            paused = not paused
            if paused and link:
                link.set("S")
        elif k == ord("q"):
            break

    if link:
        link.set("S")
        link.stop()
    src.stop()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

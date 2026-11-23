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
OBSTACLE_THR = 0.15   # fraction of the centre zone covered by objects = blocked
SIDE_BLOCKED_THR = 0.45 # side zone is only considered genuinely trapped if > 45% filled
CONF         = 0.15   # YOLO confidence (calibrated for real-time mobile camera stream)
ROI_TOP      = 0.35   # ignore the upper 35% of the image (focus on ground obstacles)
SEARCH_TURN  = "F"    # turn direction when the target is not visible
SMOOTH_N     = 3      # majority vote over the last N decisions (stops are never delayed)
SIZE         = (320, 240)   # same size as the ESP32-CAM stream

# Contour / Physical Obstacle Detection (catches blank walls, boxes, legs, and unmodeled obstacles)
ENABLE_CONTOUR_OBSTACLES = True
MIN_CONTOUR_AREA         = 550 # filter floor grain, keep substantial physical obstacles
CANNY_LOW                = 45
CANNY_HIGH               = 140

# Deadlock recovery settings:
BLOCKED_COUNT_THR = 4 # consecutive blocked cycles before triggering escape maneuver
BACKUP_DURATION   = 0.7 # seconds to back up when trapped
ESCAPE_DURATION   = 0.8 # seconds to turn away into open space
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


def enhance_frame(frame):
    """
    Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) and unsharp masking
    to recover crisp edges and object contrast from low-cost OV5640 sensors in low/uneven light.
    """
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced_lab = cv2.merge((cl, a, b))
    enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    # Mild unsharp sharpening for clearer YOLO bounding boxes
    gaussian = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
    sharpened = cv2.addWeighted(enhanced, 1.25, gaussian, -0.25, 0)
    return sharpened


# ---------------- vision ----------------
def zone_scores(frame, results):
    """
    Hybrid Obstacle Scoring:
    Combines YOLOv8 deep learning detections (people, bottles, cups, chairs)
    with edge/contour segmentation (detects untextured boxes, plain walls, table legs, barriers).
    """
    h, w = frame.shape[:2]
    y0 = int(h * ROI_TOP)
    zones = [(0, w // 3), (w // 3, 2 * w // 3), (2 * w // 3, w)]
    scores = [0.0, 0.0, 0.0]

    # 1. YOLO Detections (Red Bounding Boxes)
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

    # 2. Contour / Edge Physical Obstacle Detector (Orange Bounding Boxes)
    # Catches plain walls, boxes, and obstacles not in YOLO's 80 COCO classes
    if ENABLE_CONTOUR_OBSTACLES:
        roi = frame[y0:h, 0:w]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, CANNY_LOW, CANNY_HIGH)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            cx, cy, cw, ch = cv2.boundingRect(c)
            area = cw * ch
            # Ignore floor dust and extreme wide horizon lines
            if area > MIN_CONTOUR_AREA and cw < int(w * 0.80):
                real_y1 = cy + y0
                real_y2 = real_y1 + ch
                for i, (zx1, zx2) in enumerate(zones):
                    ox = max(0, min(cx + cw, zx2) - max(cx, zx1))
                    scores[i] += 0.4 * (ox * ch) / float((zx2 - zx1) * (h - y0))
                cv2.rectangle(frame, (cx, real_y1), (cx + cw, real_y2), (0, 140, 255), 1)

    # Clamp scores to 1.0 maximum
    scores = [min(1.0, s) for s in scores]
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


# State variables for deadlock tracking and escape maneuvers
blocked_streak = 0
escape_until = 0.0
escape_phase = None # 'BACKUP' or 'ESCAPE_TURN'
escape_turn_dir = 'R'

def decide(frame, results):
    """
    Input : frame (BGR 320x240), YOLO results
    Output: (command, state_text, zone_scores)   command is one of F, B, L, R, S
    Includes autonomous dead-end escape: when trapped, backs up and pivots away!
    """
    global blocked_streak, escape_until, escape_phase, escape_turn_dir
    scores = zone_scores(frame, results)
    left, centre, right = scores
    target = find_target(frame)
    now = time.time()

    # 1. Handle Active Escape Sequence (Never get stuck forever)
    if now < escape_until:
        if escape_phase == 'BACKUP':
            return "B", "ESCAPE_REV", scores
        elif escape_phase == 'ESCAPE_TURN':
            return escape_turn_dir, "ESCAPE_TURN", scores

    # Transition from BACKUP to ESCAPE_TURN
    if escape_phase == 'BACKUP' and now >= escape_until:
        escape_phase = 'ESCAPE_TURN'
        escape_until = now + ESCAPE_DURATION
        return escape_turn_dir, "ESCAPE_TURN", scores
    elif escape_phase == 'ESCAPE_TURN' and now >= escape_until:
        escape_phase = None
        blocked_streak = 0

    # 2. Arrived at Destination
    if target and target[1] > ARRIVED_AREA:
        blocked_streak = 0
        return "S", "ARRIVED", scores

    # 3. Obstacle Collision Prevention & Escape Triggering
    if centre > OBSTACLE_THR:
        # Genuinely deadlocked only if BOTH left and right sides are heavily impassable
        if left > SIDE_BLOCKED_THR and right > SIDE_BLOCKED_THR:
            blocked_streak += 1
            # If blocked repeatedly, initiate autonomous escape sequence:
            if blocked_streak >= BLOCKED_COUNT_THR:
                escape_phase = 'BACKUP'
                escape_until = now + BACKUP_DURATION
                # Turn toward whichever side had even slightly less density
                escape_turn_dir = "L" if left < right else "R"
                return "B", "ESCAPE_REV", scores
            return "S", "BLOCKED", scores

        # One side is freer -> steer toward the clearer side
        blocked_streak = max(0, blocked_streak - 1)
        return ("L" if left < right else "R"), "AVOID", scores

    blocked_streak = 0

    # 4. Target Navigation & Alignment
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
    """Majority vote to stop L/R flickering. STOP (S) or BACKWARD (B) execute immediately."""
    if cmd in ("S", "B"):
        history.clear()
        return cmd
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

            # Apply adaptive CLAHE and edge sharpening for low-res/noisy camera streams
            processed_frame = enhance_frame(frame)
            results = model.predict(processed_frame, imgsz=320, conf=CONF, verbose=False)
            raw_cmd, state, scores = decide(processed_frame, results)
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
            # Status colors: Green for normal, Yellow for avoid/align, Orange for escape, Red for blocked
            hud_color = (0, 255, 0)
            if "ESCAPE" in state:
                hud_color = (0, 165, 255) # Orange
            elif state in ("BLOCKED", "S"):
                hud_color = (0, 0, 255) # Red
            elif state in ("AVOID", "ALIGN"):
                hud_color = (0, 255, 255) # Yellow

            cv2.putText(frame, f"{state}  cmd={shown}  run={running}", (5, 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, hud_color, 1)
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

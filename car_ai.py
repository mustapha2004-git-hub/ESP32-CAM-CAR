import cv2, time, threading, requests
import numpy as np
from ultralytics import YOLO

# ================= SETTINGS =================
ESP_IP        = "192.168.x.x"          # your ESP32-CAM IP
STREAM_URL    = f"http://{ESP_IP}:81/stream"
CMD_URL       = f"http://{ESP_IP}/cmd"
TARGET_ID     = 0                      # ArUco marker ID placed at point B
ARRIVED_AREA  = 0.06                   # marker fraction of the frame at which we stop
OBSTACLE_THR  = 0.10                   # fraction of the centre zone covered by objects = blocked
CONF          = 0.40                   # YOLO confidence
ROI_TOP       = 0.35                   # ignore the upper part of the image (far away / sky)
SEARCH_TURN   = "R"                    # turn direction when the target is not visible
# ============================================

model = YOLO("yolov8n.pt")             # downloads automatically the first time
aruco = cv2.aruco
detector = aruco.ArucoDetector(aruco.getPredefinedDictionary(aruco.DICT_4X4_50),
                               aruco.DetectorParameters())

session = requests.Session()
last_sent = ("", 0.0)

def send(cmd):
    """Send a command; repeat it every 150 ms so the ESP32 failsafe doesn't stop the car."""
    global last_sent
    now = time.time()
    if cmd == last_sent[0] and now - last_sent[1] < 0.15:
        return
    try:
        session.get(CMD_URL, params={"d": cmd}, timeout=0.4)
    except requests.RequestException:
        pass
    last_sent = (cmd, now)

class LatestFrame(threading.Thread):
    """Reads the stream continuously and keeps only the newest frame (avoids lag)."""
    def __init__(self, url):
        super().__init__(daemon=True)
        self.url, self.frame, self.lock, self.running = url, None, threading.Lock(), True
    def run(self):
        while self.running:
            cap = cv2.VideoCapture(self.url)
            while self.running and cap.isOpened():
                ok, f = cap.read()
                if not ok:
                    break
                with self.lock:
                    self.frame = f
            cap.release()
            time.sleep(1)
    def get(self):
        with self.lock:
            return None if self.frame is None else self.frame.copy()

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
            cx = pts[:, 0].mean() / w
            cv2.polylines(frame, [pts.astype(int)], True, (0, 255, 0), 2)
            return cx, area
    return None

def decide(frame, results):
    scores = zone_scores(frame, results)
    left, centre, right = scores
    target = find_target(frame)

    # 1) Arrived at B
    if target and target[1] > ARRIVED_AREA:
        return "S", "ARRIVED", scores
    # 2) Obstacle in front: turn toward the freer side
    if centre > OBSTACLE_THR:
        if left > OBSTACLE_THR and right > OBSTACLE_THR:
            return "S", "BLOCKED", scores
        return ("L" if left < right else "R"), "AVOID", scores
    # 3) Steer toward the target
    if target:
        cx = target[0]
        if cx < 0.40: return "L", "ALIGN", scores
        if cx > 0.60: return "R", "ALIGN", scores
        return "F", "GO", scores
    # 4) No target visible: search
    return SEARCH_TURN, "SEARCH", scores

def main():
    reader = LatestFrame(STREAM_URL)
    reader.start()
    running = False
    print("Keys:  g = go   s = stop   q = quit   (starts stopped, for safety)")

    while True:
        frame = reader.get()
        if frame is None:
            time.sleep(0.05)
            continue

        results = model.predict(frame, imgsz=320, conf=CONF, verbose=False)
        cmd, state, scores = decide(frame, results)

        if state == "ARRIVED":
            running = False
        send(cmd if running else "S")

        h, w = frame.shape[:2]
        cv2.line(frame, (w // 3, 0), (w // 3, h), (255, 255, 0), 1)
        cv2.line(frame, (2 * w // 3, 0), (2 * w // 3, h), (255, 255, 0), 1)
        cv2.putText(frame, f"{state} cmd={cmd if running else 'S'} run={running}", (5, 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(frame, "L:%.2f C:%.2f R:%.2f" % tuple(scores), (5, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.imshow("car", cv2.resize(frame, None, fx=2, fy=2))

        k = cv2.waitKey(1) & 0xFF
        if k == ord("g"): running = True
        elif k == ord("s"): running = False; send("S")
        elif k == ord("q"):
            send("S")
            break

    reader.running = False
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
import threading, time
import cv2

class LatestFrame(threading.Thread):
    """Reads the ESP32 stream and keeps only the newest frame (no lag buildup)."""
    def __init__(self, url):
        super().__init__(daemon=True)
        self.url, self.frame, self.idx = url, None, 0
        self.lock, self.running, self.finished = threading.Lock(), True, False

    def run(self):
        while self.running:
            cap = cv2.VideoCapture(self.url)
            while self.running and cap.isOpened():
                ok, f = cap.read()
                if not ok:
                    break
                with self.lock:
                    self.frame, self.idx = f, self.idx + 1
            cap.release()
            time.sleep(1)

    def get(self):
        with self.lock:
            return (None if self.frame is None else self.frame.copy()), self.idx

    def stop(self):
        self.running = False
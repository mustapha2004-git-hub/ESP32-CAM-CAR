import argparse, os, time
import cv2
from stream_reader import LatestFrame

p = argparse.ArgumentParser(description="Record videos/photos from the ESP32-CAM")
p.add_argument("--ip", required=True, help="ESP32-CAM IP, e.g. 192.168.1.50")
p.add_argument("--out", default="../data/raw")
p.add_argument("--scene", default="scene", help="short name, e.g. bottle_left")
p.add_argument("--fps", type=float, default=5.0, help="playback fps of saved videos (≈ real stream fps)")
a = p.parse_args()

os.makedirs(a.out, exist_ok=True)
reader = LatestFrame(f"http://{a.ip}:81/stream")
reader.start()
print("Keys:  r = start/stop video   p = save photo   q = quit")

writer, last_idx = None, -1
while True:
    frame, idx = reader.get()
    if frame is None:
        time.sleep(0.05)
        continue
    if writer is not None and idx != last_idx:      # write each NEW frame once
        writer.write(frame)
    last_idx = idx

    view = frame.copy()
    if writer is not None:
        cv2.circle(view, (12, 12), 6, (0, 0, 255), -1)
    cv2.imshow("record", cv2.resize(view, None, fx=2, fy=2))

    k = cv2.waitKey(1) & 0xFF
    stamp = time.strftime("%Y%m%d_%H%M%S")
    if k == ord("p"):
        path = os.path.join(a.out, f"{a.scene}_{stamp}.jpg")
        cv2.imwrite(path, frame); print("saved", path)
    elif k == ord("r"):
        if writer is None:
            h, w = frame.shape[:2]
            path = os.path.join(a.out, f"{a.scene}_{stamp}.mp4")
            writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), a.fps, (w, h))
            print("recording", path)
        else:
            writer.release(); writer = None; print("stopped")
    elif k == ord("q"):
        break

if writer: writer.release()
reader.stop(); cv2.destroyAllWindows()
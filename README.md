# ESP32-CAM obstacle-avoiding car

A mini car with an ESP32-CAM (OV5640). The camera streams video over WiFi to a PC,
the PC runs the AI (YOLO + OpenCV) and sends back one command: F (forward), L, R or S (stop).

```
ESP32-CAM --video--> PC (Python AI) --F/L/R/S--> ESP32-CAM --> motors
```

## For the team: you do NOT need the car

You can develop and test everything with the recorded videos and photos.

### 1. Setup
```bash
git clone <repo-url>
cd esp32-car-ai/pc
python -m venv venv
venv\Scripts\activate        # Windows   (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
```

### 2. Run on the sample data
```bash
python car_ai.py --source ../data/samples/bottle_left.mp4
python car_ai.py --source ../data/samples          # a folder of photos
```
Keys: `space` pause, `q` quit. The window shows detected objects, the 3 zones
(left / centre / right), the decision (F/L/R/S) and the state.
Nothing is sent to any car unless you pass `--send`.

### 3. What to improve
Everything happens in `decide()` in `pc/car_ai.py`.

- **Input:** one BGR frame (320x240) and the YOLO detections.
- **Output:** one command: `F`, `L`, `R` or `S`.

Ideas: smoothing decisions over several frames (avoid flickering), detecting
obstacles YOLO doesn't know (walls, boxes) using edges or floor segmentation,
better steering toward the target, handling dead ends.

### 4. Important: realistic data
- The real camera is **320x240, about 5 fps, soft image**. Phone videos are much
  sharper, so they are automatically resized to 320x240 by the script.
  Don't tune thresholds on 1080p footage.
- At 5 fps the car moves slowly, so decisions can't depend on fast reactions.
- The image is already corrected for mirroring (left is left).
- More recordings: <GOOGLE DRIVE LINK>. Put big files there, not in git
  (GitHub limit is 100 MB per file).

## For the person with the car

Record new data:
```bash
python record_dataset.py --ip 192.168.x.x --scene obstacle_center
```
Keys: `r` start/stop video, `p` photo, `q` quit.

Run live (wheels in the air first!):
```bash
python car_ai.py --source stream --ip 192.168.x.x --send
```
Press `g` to start and `s` to stop. The car also stops by itself if commands stop
arriving for 300 ms.

## Hardware notes
- The OV5640 runs hot, so the firmware uses 10 MHz XCLK, QVGA, and reduced IO drive.
- Target point B is an ArUco marker (ID 0, 4x4 dictionary).
- Firmware: `firmware/esp32_cam_car/` (set your own WiFi name and password
  locally, never commit them).

## Workflow
Create a branch for your work (`git checkout -b yourname-feature`), push it,
and open a pull request. Don't push directly to `main`.
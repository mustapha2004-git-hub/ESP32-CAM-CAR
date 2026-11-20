# ESP32-CAM obstacle-avoiding car

A mini car with an **ESP32-CAM (OV5640)**. The camera streams video over WiFi to a PC.
The PC runs an AI (YOLO + OpenCV), decides what to do, and sends back one command:
**forward, left, right or stop**. The same ESP32-CAM board receives the command and
drives the motors through an L298N.

```
 ESP32-CAM  ---- video over WiFi ---->  PC (Python + AI)
     ^                                      |
     |                                      |  one command over WiFi
     +---- /action=FORWARD | LEFT | RIGHT | STOP
     |
  L298N driver --> 2 motors
```

**Goal:** drive from point A to point B (a printed marker) without hitting obstacles.

---

## Where we are now

| Part | Status |
|---|---|
| Camera streaming (320x240, about 5 fps, heat under control) | Working |
| AI detects objects and splits the view into left / centre / right | Working |
| AI decisions (tested live): obstacle on the right gives `L`, on the left gives `R`, big obstacle in front gives `S` | Working |
| Car driven by the AI commands through the L298N | Wired and answering commands, floor tests in progress |
| Smarter decisions (walls, smoothing, reaching point B reliably) | **This is where the team can help** |

---

## For the team: you do NOT need the car

Everything about the decision logic can be developed with the recorded videos and photos.

### 1. Setup (Windows, once)

You need **Python 3.10, 3.11 or 3.12**. Newer versions (3.13+) often do not work with the AI libraries.

```bash
git clone <repo-url>
cd <repo-folder>/pc
py -3.12 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Linux / Mac: use `python3 -m venv venv` and `source venv/bin/activate`.

Notes:
- The prompt must start with `(venv)` after activating. Do this **every time** you open a new terminal.
- If PowerShell blocks `activate`, run `Set-ExecutionPolicy -Scope Process Bypass` first.
- Always install with `python -m pip` (plain `pip` can belong to another Python version and gives "No module named cv2").
- The first run downloads the AI model `yolov8n.pt` (about 6 MB), so you need internet **once**.

### 2. Run the AI on a sample video

```bash
python car_ai.py --source ../data/samples/FILE_NAME.mp4
```

Use any `.mp4` from `data/samples/`. A window opens:

| On screen | Meaning |
|---|---|
| Red boxes | Objects found by YOLO |
| Two blue / yellow vertical lines | The three zones: left, centre, right |
| `L:0.00 C:0.00 R:0.00` | How much of each zone is covered by objects (0 to 1) |
| Top text: `AVOID cmd=L` | The state and the command the AI would send |

Keys: `space` pause, `q` quit. **Nothing is sent to any car unless you add `--send`.**

To run on photos instead, point `--source` at a folder that contains `.jpg` / `.png` files.
(A folder with only `.mp4` files will show nothing; give a single video file instead.)

### 3. Score all videos automatically

`data/samples/labels.csv` says which command is correct for each clip:

```
obstacle_center_left_free_20261116_153000.mp4,L
blocked_all_20261116_154000.mp4,S
```

Then run:

```bash
python evaluate_clips.py ../data/samples
```

It prints, for every clip, the expected command, the most common command the AI gave,
the percentage of each command (for example `L:72% R:20% S:8%`), and PASS / FAIL.
**Use this score to prove that your version of `decide()` is better than the previous one.**

### 4. What to improve

Everything happens in the function `decide()` in `pc/car_ai.py`.

- **Input:** one BGR frame (320x240) and the YOLO detections.
- **Output:** a command `F`, `L`, `R` or `S`, a state text, and the three zone scores.

How it decides today (in this order):

| Situation | State | Command |
|---|---|---|
| Marker (ArUco ID 0) is big, so we arrived | `ARRIVED` | `S` |
| Object in the centre, one side freer | `AVOID` | `L` or `R` toward the freer side |
| Left, centre and right all blocked | `BLOCKED` | `S` |
| Marker visible on the left / right | `ALIGN` | `L` / `R` |
| Marker visible in the centre | `GO` | `F` |
| Nothing detected | `SEARCH` | `F` (set by `SEARCH_TURN`) |

Settings at the top of `car_ai.py`: `OBSTACLE_THR`, `CONF`, `ROI_TOP`, `SEARCH_TURN`,
`SMOOTH_N`, `ARRIVED_AREA`, `TARGET_ID`.

A small majority vote over the last 3 decisions already reduces left/right flicker (`SMOOTH_N`).
A stop is never delayed.

**Ideas, from most useful to least:**
1. **Plain walls and boxes are often missed** (YOLO only knows certain objects like bottle, chair, cup, person). Detect them with edges, floor segmentation, or "the image gets blurry / uniform when close".
2. Remember where the marker was last seen and turn back toward it when it is lost.
3. Better steering toward the marker (smaller turns instead of full spins).
4. Handle dead ends (blocked on all sides: back up, then turn).
5. Smarter smoothing without adding delay to stops.

### 5. Important: realistic data

- The real camera is **320x240, about 5 fps, soft picture**. Phone videos are much sharper, so
  the scripts resize them to 320x240 automatically. **Do not tune thresholds on 1080p footage.**
- At 5 fps the car reacts about 0.2 to 0.5 seconds late, so decisions must be safe and simple.
- The picture is already corrected for mirroring: **left is left**.
- The camera is slow in dim light, so test with bright light too.
- More recordings: <GOOGLE DRIVE LINK>. Put big files there, not in git (GitHub limit is 100 MB per file).

---

## For the person with the car

### Hardware

| Part | Notes |
|---|---|
| ESP32-CAM, AI-Thinker style, with OV5640 | Programmed with the ESP32-CAM-MB USB board |
| L298N motor driver + 2 DC motors | **ENA and ENB jumpers stay ON** (full speed, no speed pins) |
| Motor battery (about 6.5 V) | Only connected to the L298N (12V terminal) |
| Lithium 3.7 V + boost converter set to 5.0 V | Powers the ESP32-CAM (5V pin) |
| 470 uF capacitor | Across the ESP32-CAM 5V and GND |
| Printed ArUco marker, ID 0 (4x4 dictionary) | Placed at point B |

### Wiring (final pins that work)

| ESP32-CAM | L298N | Function |
|---|---|---|
| GPIO 13 | IN1 | Left motor direction |
| GPIO 15 | IN2 | Left motor direction |
| GPIO 14 | IN3 | Right motor direction |
| GPIO 2 | IN4 | Right motor direction |
| GND | GND | **Common ground (required)** |

- L298N OUT1/OUT2 go to the left motor, OUT3/OUT4 to the right motor.
- Motor battery + goes to the L298N 12V terminal, battery - goes to the L298N GND terminal.
- Boost converter OUT+ (5.0 V) goes to the ESP32-CAM 5V pin, OUT- goes to the GND pin.
- **Only the grounds are joined** between the two batteries. Never join the two + wires.
- Do not use the USB programmer at the same time as the battery.
- GPIO 15 and GPIO 2 are boot pins: if the upload fails, unplug the IN2 and IN4 wires, upload, then plug them back.
- The camera uses GPIO 5, 18, 19, 21, 22 and 23, which is why the motors use the free pins 13, 15, 14 and 2.

### What each command does

| Link | Short | Result |
|---|---|---|
| `/action=FORWARD` | F | Both wheels forward |
| `/action=BACKWARD` | B | Both wheels backward |
| `/action=LEFT` | L | Spin left (left wheel back, right forward) |
| `/action=RIGHT` | R | Spin right (left wheel forward, right back) |
| `/action=STOP` | S | Stop |

Safety: the car **stops by itself** if no command arrives for 0.3 seconds, or if WiFi is lost.
(So in a browser the wheels only turn for a moment. That is normal.)
The older links `/cmd?d=F` (F, B, L, R, S) also work.

### Firmware (Arduino IDE)

File: `firmware/esp32_cam_car/esp32_cam_car.ino`

- Board: **AI Thinker ESP32-CAM**, PSRAM: **Enabled**, Partition scheme: **Huge APP**.
- Enter your **own WiFi name and password** in the file **locally**. **Never commit them to GitHub.**
  Use a 2.4 GHz network (a phone hotspot worked best; the home router gave about 1 fps).
- Upload, open the Serial Monitor at 115200 baud, press RST, and read the line `Ready: http://...`.
  That is the IP address (it changes with the hotspot).

Heat settings (the OV5640 runs hot): 10 MHz camera clock, 320x240, one frame buffer,
40 ms pause between frames, reduced sensor drive strength, WiFi power 15 dBm, flash LED off.
If it is still too hot: lower `XCLK_FREQ` to 8000000, add a small heatsink on the back of the camera.

### Step-by-step test (do not skip steps)

Replace `CAM_IP` with the IP address.

1. **Camera:** open `http://CAM_IP:81/stream` in a browser. You should see the picture. **Close the tab afterwards**
   (the stream serves only one viewer, and the Python script needs it).
2. **Wheels in the air.** Open `http://CAM_IP/action=FORWARD`. Both wheels must go forward, then stop after about 0.3 s.
   - One wheel wrong: swap that motor's two wires.
   - Both wheels backward: set `SWAP_MOTOR_DIRECTION` to 1 in the sketch.
   - Check `LEFT` and `RIGHT` too.
3. **AI without moving the car:**
   ```bash
   python car_ai.py --source stream --ip CAM_IP
   ```
   Put a bottle in the centre, on the left, on the right. Check the states and commands.
4. **AI drives, wheels in the air:**
   ```bash
   python car_ai.py --source stream --ip CAM_IP --motor-ip CAM_IP --send
   ```
   The camera and the motors are on the same board, so both options use the same address.
   The car starts **stopped**. Press `g` to allow movement, `s` to stop, `space` to pause, `q` to quit (it sends a stop).
5. **Floor test:** a large empty area, one obstacle about 1 m in front, the marker beyond it.
   Keep a finger on `s`. The motors run at **full speed**, so be careful.

### Record new data

```bash
python record_dataset.py --ip CAM_IP --scene obstacle_center
```

Keys: `r` start/stop video, `p` save a photo, `q` quit. Files go to `data/raw/` (ignored by git).
Copy the good ones to `data/samples/` and add a line for each in `labels.csv`, then push.

Scenes worth recording (10 to 20 seconds each): clear path, obstacle in the centre with the left free,
the same with the right free, objects on the left only, on the right only, blocked on all sides,
a gap in the middle, a plain wall close, an object approaching, the marker on the left / centre / right,
bright and dim light. Hold the camera at the car's height (a few cm above the floor).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named cv2` | Activate the venv (`venv\Scripts\activate`) and install with `python -m pip install -r requirements.txt` |
| Stream connection failed | PC and ESP32-CAM must be on the **same WiFi**. Check the IP. Test with `ping CAM_IP` |
| Window stays black | Close any browser tab or phone that also views the stream |
| Model download fails | The first run needs internet once. Afterwards it works offline |
| No red boxes | Use objects YOLO knows (bottle, cup, chair, person), good light, or lower `CONF` to 0.25 |
| Reacts to the floor | Raise `ROI_TOP` (try 0.5) |
| Reacts too late | Lower `OBSTACLE_THR` (try 0.05) |
| Car moves but turns the wrong way | Swap the left and right motor connections. Also check that the mirror setting is on |
| Camera board resets when the motors start | Keep the separate batteries, check the 470 uF capacitor, charge the batteries |
| Camera too hot | Lower the camera clock to 8 MHz, add a heatsink |

---

## Known limits

- About **5 fps** and 320x240, so the car must move slowly.
- YOLO only recognises certain objects, so **plain walls and boxes can be missed** and the car can drive into them.
  A front ultrasonic sensor would fix this.
- Without a marker in view, the car drives forward and avoids what it sees. It does not know where B is.
- The AI runs on the PC, so the car needs WiFi.

---

## Project layout

```
firmware/esp32_cam_car/esp32_cam_car.ino   code on the ESP32-CAM (stream + motor commands)
pc/car_ai.py                               the AI and the decision function decide()
pc/stream_reader.py                        reads the camera stream (newest frame only)
pc/record_dataset.py                       records videos and photos from the camera
pc/evaluate_clips.py                       scores the AI on labelled videos
pc/requirements.txt                        Python libraries
data/samples/                              short test clips and labels.csv
```

## Workflow

Create a branch for your work (`git checkout -b yourname-feature`), push it, and open a pull request.
Do not push directly to `main`. In the pull request, include the output of `evaluate_clips.py`
before and after your change.

Never commit WiFi names or passwords.

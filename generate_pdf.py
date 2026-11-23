import os, sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        # Draw header
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#334155"))
        self.drawString(40, 755, "ESP32-CAM AI OBSTACLE-AVOIDING CAR")
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawRightString(612 - 40, 755, "System Architecture & Engineering Manual")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(40, 749, 612 - 40, 749)

        # Draw footer
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(40, 36, 612 - 40, 36)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(40, 26, "Antigravity Engineering Brief - Robotics & Embedded Vision")
        self.drawRightString(612 - 40, 26, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def build_pdf(filename="ESP32_CAM_Car_Documentation.pdf"):
    # Total width: 612, total height: 792.
    # Margins: 40 left/right -> usable width = 532 pt
    # Margins: 44 top, 42 bottom -> usable height = 706 pt
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=44,
        bottomMargin=42
    )

    styles = getSampleStyleSheet()

    primary_color = colors.HexColor("#1E3A8A")     # Navy Blue
    secondary_color = colors.HexColor("#0D9488")   # Teal
    dark_neutral = colors.HexColor("#1E293B")      # Slate 800
    accent_danger = colors.HexColor("#B91C1C")     # Crimson

    styles.add(ParagraphStyle(
        name='CoverPre',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=secondary_color,
        spaceAfter=2
    ))
    styles.add(ParagraphStyle(
        name='CoverTitle',
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name='CoverSubtitle',
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=dark_neutral,
        spaceAfter=7
    ))
    styles.add(ParagraphStyle(
        name='CoverMeta',
        fontName='Helvetica',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#475569")
    ))
    styles.add(ParagraphStyle(
        name='SecHeading',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=primary_color,
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        name='SubHeading',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=secondary_color,
        spaceBefore=4,
        spaceAfter=2,
        keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        name='BodyDoc',
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.8,
        textColor=dark_neutral,
        spaceAfter=3
    ))
    styles.add(ParagraphStyle(
        name='BulletDoc',
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.8,
        textColor=dark_neutral,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2.5
    ))
    styles.add(ParagraphStyle(
        name='TableHead',
        fontName='Helvetica-Bold',
        fontSize=7.4,
        leading=9.5,
        textColor=colors.white
    ))
    styles.add(ParagraphStyle(
        name='TableCell',
        fontName='Helvetica',
        fontSize=7.0,
        leading=9.0,
        textColor=dark_neutral
    ))
    styles.add(ParagraphStyle(
        name='TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=7.0,
        leading=9.0,
        textColor=dark_neutral
    ))
    styles.add(ParagraphStyle(
        name='CalloutText',
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.8,
        textColor=colors.HexColor("#1E293B")
    ))

    def make_callout(text, bg="#F1F5F9", border="#94A3B8", width=532, title=None):
        content = []
        if title:
            content.append(Paragraph(f"<b>{title}</b>", ParagraphStyle(
                'CTitle', fontName='Helvetica-Bold', fontSize=7.5, leading=9.5,
                textColor=border if isinstance(border, colors.Color) else colors.HexColor(border),
                spaceAfter=1.5
            )))
        content.append(Paragraph(text, styles['CalloutText']))
        t = Table([[content]], colWidths=[width])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(bg) if isinstance(bg, str) else bg),
            ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor(border) if isinstance(border, str) else border),
            ('LINELEFT', (0,0), (-1,-1), 3.0, colors.HexColor(border) if isinstance(border, str) else border),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        return t

    story = []

    # ================= PAGE 1: TITLE, EXECUTIVE SUMMARY & ARCHITECTURE DIAGRAM =================
    story.append(Paragraph("PROJECT ONBOARDING & ARCHITECTURAL SPECIFICATION", styles['CoverPre']))
    story.append(Paragraph("ESP32-CAM Autonomous Obstacle-Avoiding Car", styles['CoverTitle']))
    story.append(Paragraph("Engineering Reference: Edge Perception, Offboard Neural Inference & Actuation", styles['CoverSubtitle']))

    # Metadata Grid
    meta_data = [
        [
            Paragraph("<b>Target Audience:</b> New Engineers, Researchers, Developers", styles['CoverMeta']),
            Paragraph("<b>Hardware Target:</b> AI-Thinker ESP32-CAM (OV5640) + L298N", styles['CoverMeta'])
        ],
        [
            Paragraph("<b>AI / Software Stack:</b> Ultralytics YOLOv8n + OpenCV 4 + ArUco", styles['CoverMeta']),
            Paragraph("<b>Navigation Goal:</b> Point A to Point B (ArUco Target) Collision-Free", styles['CoverMeta'])
        ]
    ]
    t_meta = Table(meta_data, colWidths=[266, 266])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor("#E2E8F0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 4))

    story.append(Paragraph("1. System Architecture & Split-Perception Model", styles['SecHeading']))
    story.append(Paragraph(
        "To navigate autonomously while overcoming the severe memory and thermal limits of microcontrollers, "
        "the system divides computation into an onboard sensor/actuator node and an offboard workstation:",
        styles['BodyDoc']
    ))
    story.append(Paragraph("<b>Embedded Node (ESP32-CAM):</b> Streams OV5640 QVGA video over Wi-Fi (Port 81) and drives dual motors via L298N H-Bridge (Port 80).", styles['BulletDoc']))
    story.append(Paragraph("<b>Workstation (PC Python):</b> Low-latency frame ingestion, YOLOv8 spatial zone scoring, ArUco 4x4 fiducial tracking, and telemetry control.", styles['BulletDoc']))

    story.append(Spacer(1, 3))
    # Embedded High-Resolution Architecture Diagram (532 pt wide x 230 pt high)
    arch_img_path = r"C:\Users\MOUAD\Desktop\ESP32-CAM-CAR-main\assets\system_architecture.png"
    if os.path.exists(arch_img_path):
        img_arch = Image(arch_img_path, width=532, height=230)
        story.append(img_arch)
        story.append(Spacer(1, 3))

    arch_table_data = [
        [Paragraph("<b>Subsystem</b>", styles['TableHead']), Paragraph("<b>Component</b>", styles['TableHead']), Paragraph("<b>Role, Specifications & Interfaces</b>", styles['TableHead'])],
        [
            Paragraph("<b>Vision Source</b>", styles['TableCellBold']),
            Paragraph("ESP32-CAM (OV5640)", styles['TableCell']),
            Paragraph("QVGA (320x240) JPEG @ ~5 FPS. 10 MHz XCLK, single frame-buffer in PSRAM, 40ms inter-frame rest to control heat. Streams on Port 81.", styles['TableCell'])
        ],
        [
            Paragraph("<b>Telemetry Channel</b>", styles['TableCellBold']),
            Paragraph("802.11b/g/n Wi-Fi<br/>Dual HTTP Daemons", styles['TableCell']),
            Paragraph("Dual HTTP servers: Port 81 for video; Port 80 for low-latency commands (/action=FORWARD, etc.) and telemetry (/status).", styles['TableCell'])
        ],
        [
            Paragraph("<b>PC Intelligence</b>", styles['TableCellBold']),
            Paragraph("Python 3.10-3.12<br/>YOLOv8n + OpenCV", styles['TableCell']),
            Paragraph("Pulls newest unlagged frame; runs Left/Center/Right zone slicing, ArUco ID 0 centroid tracking, and decision state machine.", styles['TableCell'])
        ],
        [
            Paragraph("<b>Actuation & Power</b>", styles['TableCellBold']),
            Paragraph("L298N + TT Motors<br/>Isolated Supplies", styles['TableCell']),
            Paragraph("Differential steering on GPIO 13, 15, 14, 2. 300ms watchdog cutoff. Split batteries: 6.5V motor + 5.0V boosted logic (Common GND).", styles['TableCell'])
        ]
    ]
    t_arch = Table(arch_table_data, colWidths=[85, 105, 342])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 3))

    story.append(make_callout(
        "<b>Fail-Safe Watchdog:</b> Hardware timer cuts motor drive to STOP if Wi-Fi or PC heartbeat ceases for >300 ms. In software, any STOP decision immediately purges the smoothing queue and executes instantly.",
        bg="#EFF6FF", border="#3B82F6", width=532, title="FAIL-SAFE GUARANTEE"
    ))

    story.append(PageBreak())

    # ================= PAGE 2: HARDWARE MATERIALS & COMPLETE WIRING SCHEMATIC =================
    story.append(Paragraph("2. Hardware Bill of Materials & Wiring Schematic", styles['SecHeading']))
    story.append(Paragraph(
        "Inductive motor transients will instantly reset microcontrollers if supplies are not isolated. "
        "Review the complete interconnect map below before powering up:",
        styles['BodyDoc']
    ))

    # Embedded Schematic Diagram (532 pt wide x 235 pt high)
    schem_img_path = r"C:\Users\MOUAD\Desktop\ESP32-CAM-CAR-main\assets\wiring_schematic.png"
    if os.path.exists(schem_img_path):
        img_schem = Image(schem_img_path, width=532, height=235)
        story.append(img_schem)
        story.append(Spacer(1, 3))

    wiring_data = [
        [Paragraph("<b>Source Pin</b>", styles['TableHead']), Paragraph("<b>Target Pin</b>", styles['TableHead']), Paragraph("<b>Signal Type</b>", styles['TableHead']), Paragraph("<b>Functional Role & Boot Pin Precautions</b>", styles['TableHead'])],
        [Paragraph("ESP32-CAM <b>GPIO 13</b>", styles['TableCell']), Paragraph("L298N <b>IN1</b>", styles['TableCellBold']), Paragraph("Digital Out", styles['TableCell']), Paragraph("Left Motor Direction A. High = Forward.", styles['TableCell'])],
        [Paragraph("ESP32-CAM <b>GPIO 15</b>", styles['TableCell']), Paragraph("L298N <b>IN2</b>", styles['TableCellBold']), Paragraph("Digital Out", styles['TableCell']), Paragraph("Left Motor Direction B. <i>Boot pin: Unplug wire if firmware flash fails.</i>", styles['TableCell'])],
        [Paragraph("ESP32-CAM <b>GPIO 14</b>", styles['TableCell']), Paragraph("L298N <b>IN3</b>", styles['TableCellBold']), Paragraph("Digital Out", styles['TableCell']), Paragraph("Right Motor Direction A. High = Forward.", styles['TableCell'])],
        [Paragraph("ESP32-CAM <b>GPIO 2</b>", styles['TableCell']), Paragraph("L298N <b>IN4</b>", styles['TableCellBold']), Paragraph("Digital Out", styles['TableCell']), Paragraph("Right Motor Direction B. <i>Boot pin: Unplug wire if firmware flash fails.</i>", styles['TableCell'])],
        [Paragraph("ESP32-CAM <b>GND</b>", styles['TableCell']), Paragraph("L298N <b>GND</b>", styles['TableCellBold']), Paragraph("Common GND", styles['TableCell']), Paragraph("<b>MANDATORY:</b> Common reference. Never tie positive supply rails together!", styles['TableCell'])],
        [Paragraph("L298N <b>OUT1 / OUT2</b>", styles['TableCell']), Paragraph("Left TT Motor (+/-)", styles['TableCell']), Paragraph("Power Drive", styles['TableCell']), Paragraph("Reversing leads inverts Left wheel rotational vector.", styles['TableCell'])],
        [Paragraph("L298N <b>OUT3 / OUT4</b>", styles['TableCell']), Paragraph("Right TT Motor (+/-)", styles['TableCell']), Paragraph("Power Drive", styles['TableCell']), Paragraph("Reversing leads inverts Right wheel rotational vector.", styles['TableCell'])],
        [Paragraph("Motor Batt <b>(+6.5V)</b>", styles['TableCell']), Paragraph("L298N <b>12V Screw</b>", styles['TableCellBold']), Paragraph("High Current", styles['TableCell']), Paragraph("Powers motor coils directly. DO NOT connect to ESP32 5V rail.", styles['TableCell'])],
        [Paragraph("Boost Out <b>(+5.0V)</b>", styles['TableCell']), Paragraph("ESP32 <b>5V Pin</b>", styles['TableCellBold']), Paragraph("Regulated 5V", styles['TableCell']), Paragraph("Powers ESP32. Solder 470 µF capacitor across 5V and GND directly.", styles['TableCell'])]
    ]
    t_wire = Table(wiring_data, colWidths=[95, 95, 75, 267])
    t_wire.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_wire)
    story.append(Spacer(1, 3))

    story.append(make_callout(
        "<b>CRITICAL ELECTRICAL HAZARDS:</b><br/>"
        "1. <b>Strict Voltage Isolation:</b> The 6.5V motor battery and 5.0V logic supply must NEVER be bridged on their positive poles. Only GND is common.<br/>"
        "2. <b>Boot Pin Strapping:</b> GPIO 2 and 15 affect ESP32 boot state. If Arduino IDE reports <i>'Failed to connect'</i>, temporarily disconnect L298N IN2 and IN4 wires while flashing.<br/>"
        "3. <b>Dual Powering Prohibited:</b> Disconnect battery power before plugging in USB programming shields.",
        bg="#FEF2F2", border=accent_danger, width=532, title="SAFETY & RELIABILITY WARNING"
    ))

    story.append(PageBreak())

    # ================= PAGE 3: SOFTWARE PROTOCOL & AI VISION LOGIC =================
    story.append(Paragraph("3. Software Protocol & AI Vision Architecture", styles['SecHeading']))
    story.append(Paragraph(
        "The firmware and PC workstation communicate over HTTP via a high-performance, non-blocking telemetry protocol:",
        styles['BodyDoc']
    ))

    proto_data = [
        [Paragraph("<b>Port / Service</b>", styles['TableHead']), Paragraph("<b>Endpoint URI</b>", styles['TableHead']), Paragraph("<b>Protocol & Format</b>", styles['TableHead']), Paragraph("<b>Functional Role & Handling</b>", styles['TableHead'])],
        [Paragraph("<b>Port 81 (Stream)</b>", styles['TableCellBold']), Paragraph("<code>/stream</code>", styles['TableCell']), Paragraph("MJPEG Multipart Chunked", styles['TableCell']), Paragraph("Dedicated socket; delivers 320x240 frames. Single client limit prevents memory leaks.", styles['TableCell'])],
        [Paragraph("<b>Port 80 (Drive)</b>", styles['TableCellBold']), Paragraph("<code>/action=FORWARD|BACKWARD|<br/>LEFT|RIGHT|STOP</code>", styles['TableCell']), Paragraph("HTTP 200 ('OK')<br/>Accepts wildcard <code>/action=*&ai=1</code>", styles['TableCell']), Paragraph("Heartbeat drive endpoint. Configures GPIO 13, 15, 14, 2 H-Bridge levels. Resets 300ms watchdog.", styles['TableCell'])],
        [Paragraph("<b>Port 80 (Status)</b>", styles['TableCellBold']), Paragraph("<code>/status</code>", styles['TableCell']), Paragraph("JSON object telemetry", styles['TableCell']), Paragraph("Returns: <code>{\"camera\":bool, \"moving\":bool, \"uptime_s\":int, \"rssi\":int, \"heap_kb\":int}</code>.", styles['TableCell'])],
        [Paragraph("<b>Port 80 (Power)</b>", styles['TableCellBold']), Paragraph("<code>/on</code> & <code>/off</code>", styles['TableCell']), Paragraph("Hardware PWDN control", styles['TableCell']), Paragraph("Puts OV5640 into deep sleep mode between test runs to avoid sensor thermal degradation.", styles['TableCell'])]
    ]
    t_proto = Table(proto_data, colWidths=[85, 125, 132, 190])
    t_proto.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_proto)
    story.append(Spacer(1, 4))

    story.append(Paragraph("Spatial Vision Pipeline (car_ai.py)", styles['SubHeading']))
    story.append(Paragraph("<b>1. LatestFrame Buffer Flush:</b> Standard OpenCV queues create a fatal 2s latency. <code>stream_reader.py</code> runs a dedicated background reader thread and discards stale frames, yielding 0-latency live perception.", styles['BulletDoc']))
    story.append(Paragraph("<b>2. ROI Elevation Masking:</b> The top 35% of the frame (<code>ROI_TOP = 0.35</code>) is excluded from obstacle scoring. This ignores ceiling lights and far walls, isolating objects on the driving surface.", styles['BulletDoc']))
    story.append(Paragraph("<b>3. Tri-Zone Obstacle Slicing:</b> The frame is vertically split into Left (0-106px), Center (107-213px), and Right (214-320px). Detected bounding boxes (YOLOv8n, conf >= 0.40) contribute to zone coverage fractions (0.0 to 1.0).", styles['BulletDoc']))
    story.append(Paragraph("<b>4. ArUco Destination Alignment:</b> Detects 4x4 ArUco Marker ID 0. Centroid fraction (cx) guides turning; bounding area > 6% triggers destination arrival.", styles['BulletDoc']))

    story.append(Spacer(1, 4))
    story.append(Paragraph("Finite State Machine Decision Matrix (decide())", styles['SubHeading']))

    fsm_data = [
        [Paragraph("<b>State</b>", styles['TableHead']), Paragraph("<b>Sensory Condition (Visual & Target)</b>", styles['TableHead']), Paragraph("<b>Cmd</b>", styles['TableHead']), Paragraph("<b>Dynamic Action & Description</b>", styles['TableHead'])],
        [Paragraph("<b>ARRIVED</b>", styles['TableCellBold']), Paragraph("Target ArUco ID 0 area > 6% (<code>ARRIVED_AREA</code>)", styles['TableCell']), Paragraph("<b>S</b>", styles['TableCellBold']), Paragraph("Goal achieved. Immediate full stop.", styles['TableCell'])],
        [Paragraph("<b>BLOCKED</b>", styles['TableCellBold']), Paragraph("Center > 10% AND Left > 10% AND Right > 10%", styles['TableCell']), Paragraph("<b>S</b>", styles['TableCellBold']), Paragraph("Trap prevention: halts vehicle to avoid collision.", styles['TableCell'])],
        [Paragraph("<b>AVOID</b>", styles['TableCellBold']), Paragraph("Center > 10% (<code>OBSTACLE_THR</code>), side free", styles['TableCell']), Paragraph("<b>L / R</b>", styles['TableCellBold']), Paragraph("Steers toward freer side: Left if score_L < score_R else Right.", styles['TableCell'])],
        [Paragraph("<b>ALIGN</b>", styles['TableCellBold']), Paragraph("Center clean, Target visible at cx < 0.40", styles['TableCell']), Paragraph("<b>L</b>", styles['TableCellBold']), Paragraph("Spins left to bring marker into camera center.", styles['TableCell'])],
        [Paragraph("<b>ALIGN</b>", styles['TableCellBold']), Paragraph("Center clean, Target visible at cx > 0.60", styles['TableCell']), Paragraph("<b>R</b>", styles['TableCellBold']), Paragraph("Spins right to bring marker into camera center.", styles['TableCell'])],
        [Paragraph("<b>GO</b>", styles['TableCellBold']), Paragraph("Center clean, Target centered (0.40 <= cx <= 0.60)", styles['TableCell']), Paragraph("<b>F</b>", styles['TableCellBold']), Paragraph("Drives forward directly toward destination.", styles['TableCell'])],
        [Paragraph("<b>SEARCH</b>", styles['TableCellBold']), Paragraph("Center clean, Target ArUco not in frame", styles['TableCell']), Paragraph("<b>F</b>", styles['TableCellBold']), Paragraph("Default search trajectory (configurable via <code>SEARCH_TURN</code>).", styles['TableCell'])]
    ]
    t_fsm = Table(fsm_data, colWidths=[65, 207, 40, 220])
    t_fsm.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), secondary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_fsm)
    story.append(Spacer(1, 4))

    story.append(make_callout(
        "<b>Asymmetric Smoothing Invariant:</b> Motor commands pass through a 3-frame rolling majority vote (<code>SMOOTH_N = 3</code>) to filter out single-frame perception flickers. However, <b>STOP commands completely bypass smoothing and execute immediately</b>.",
        bg="#F8FAFC", border="#64748B", width=532, title="SMOOTHING LOGIC"
    ))

    story.append(PageBreak())

    # ================= PAGE 4: SETUP, BENCHMARKING, ROADMAP & TROUBLESHOOTING =================
    story.append(Paragraph("4. Developer Onboarding, Benchmarking & Diagnostics", styles['SecHeading']))
    story.append(Paragraph(
        "To contribute code, developers clone the repository and evaluate their algorithms against the benchmark dataset:",
        styles['BodyDoc']
    ))

    setup_p = [
        "<b>1. Python Environment:</b> Python 3.10 to 3.12 is required (Python 3.13 is unsupported by torch/ultralytics).",
        "<b>2. Setup Virtualenv:</b> <code>py -3.12 -m venv venv</code> -> <code>venv\\Scripts\\activate</code> (Windows) / <code>source venv/bin/activate</code> (Linux/Mac).",
        "<b>3. Install Packages:</b> <code>python -m pip install -r requirements.txt</code> (installs opencv-python, ultralytics, requests, numpy).",
        "<b>4. Replay Sample Videos:</b> Run <code>python car_ai.py --source ../data/samples/turn_left.mp4</code>. Observe bounding boxes and zone metrics.",
        "<b>5. Run Quantitative Benchmark:</b> Execute <code>python evaluate_clips.py ../data/samples</code> to verify accuracy against ground-truth labels."
    ]
    for sp in setup_p:
        story.append(Paragraph(sp, styles['BulletDoc']))

    story.append(Spacer(1, 3))
    story.append(Paragraph("Live Driving Keystrokes (--send mode)", styles['SubHeading']))

    ctrl_data = [
        [Paragraph("<b>Key</b>", styles['TableHead']), Paragraph("<b>Action</b>", styles['TableHead']), Paragraph("<b>Description & Safe Operating Protocol</b>", styles['TableHead'])],
        [Paragraph("<b>g</b>", styles['TableCellBold']), Paragraph("Go / Arm", styles['TableCell']), Paragraph("Arms driving thread; vehicle starts moving based on AI decisions.", styles['TableCell'])],
        [Paragraph("<b>s</b>", styles['TableCellBold']), Paragraph("Emergency Stop", styles['TableCell']), Paragraph("Disarms driving thread, immediately sends <code>/action=STOP</code> to car.", styles['TableCell'])],
        [Paragraph("<b>[Space]</b>", styles['TableCellBold']), Paragraph("Pause / Freeze", styles['TableCell']), Paragraph("Freezes video frame for analysis while halting motor movement.", styles['TableCell'])],
        [Paragraph("<b>q</b>", styles['TableCellBold']), Paragraph("Quit & Shutdown", styles['TableCell']), Paragraph("Transmits stop heartbeat, joins threads, releases camera, closes windows.", styles['TableCell'])]
    ]
    t_ctrl = Table(ctrl_data, colWidths=[40, 100, 392])
    t_ctrl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_ctrl)
    story.append(Spacer(1, 4))

    story.append(Paragraph("Algorithm Improvement Tasks (decide() in car_ai.py)", styles['SubHeading']))
    tasks_data = [
        [Paragraph("<b>Priority Area</b>", styles['TableHead']), Paragraph("<b>Current Limitation</b>", styles['TableHead']), Paragraph("<b>Recommended Technical Solution</b>", styles['TableHead'])],
        [Paragraph("<b>1. Untextured Walls</b>", styles['TableCellBold']), Paragraph("YOLO only detects COCO objects (chairs, cups); blank walls are missed.", styles['TableCell']), Paragraph("Implement Canny edge density or floor HSV color segmentation.", styles['TableCell'])],
        [Paragraph("<b>2. Target Amnesia</b>", styles['TableCellBold']), Paragraph("Losing marker during avoidance triggers dumb forward SEARCH.", styles['TableCell']), Paragraph("Store last seen target vector (cx, cy) and recover orientation.", styles['TableCell'])],
        [Paragraph("<b>3. Dead-End Handling</b>", styles['TableCellBold']), Paragraph("When all 3 zones block, vehicle stops forever with no exit strategy.", styles['TableCell']), Paragraph("Trigger reverse escape macro: BACKWARD for 0.8s, then spin right.", styles['TableCell'])],
        [Paragraph("<b>4. Speed & Latency</b>", styles['TableCellBold']), Paragraph("5 FPS creates ~250ms latency; motors run full speed at all times.", styles['TableCell']), Paragraph("Implement PWM speed throttling or widen Center obstacle threshold.", styles['TableCell'])]
    ]
    t_tasks = Table(tasks_data, colWidths=[95, 195, 242])
    t_tasks.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), secondary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_tasks)
    story.append(Spacer(1, 4))

    story.append(Paragraph("Hardware & Software Troubleshooting Guide", styles['SubHeading']))
    trb_data = [
        [Paragraph("<b>Symptom</b>", styles['TableHead']), Paragraph("<b>Root Cause</b>", styles['TableHead']), Paragraph("<b>Corrective Action</b>", styles['TableHead'])],
        [Paragraph("ESP32 resets continuously", styles['TableCellBold']), Paragraph("Brownout on Wi-Fi TX burst", styles['TableCell']), Paragraph("Check 470 µF capacitor across 5V/GND; ensure battery voltage > 4.8V under load.", styles['TableCell'])],
        [Paragraph("Camera error 0x20003", styles['TableCellBold']), Paragraph("OV5640 overheating / bad clock", styles['TableCell']), Paragraph("Keep XCLK at 10 MHz; FRAME_DELAY_MS = 40; attach small heatsink to camera.", styles['TableCell'])],
        [Paragraph("Flash error: Failed to connect", styles['TableCellBold']), Paragraph("GPIO 2 / 15 held by L298N", styles['TableCell']), Paragraph("Temporarily unplug jumper wires from L298N IN2 & IN4 while flashing firmware.", styles['TableCell'])],
        [Paragraph("Car turns wrong direction", styles['TableCellBold']), Paragraph("Inverted motor wiring / mirror", styles['TableCell']), Paragraph("Ensure <code>IMAGE_HMIRROR 1</code> in firmware. Invert L298N motor wire pairs.", styles['TableCell'])],
        [Paragraph("Stream black or freezing", styles['TableCellBold']), Paragraph("Multiple browser client tabs", styles['TableCell']), Paragraph("Close all open browser tabs accessing <code>:81/stream</code> before starting Python.", styles['TableCell'])]
    ]
    t_trb = Table(trb_data, colWidths=[110, 150, 272])
    t_trb.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_trb)

    doc.build(story, canvasmaker=NumberedCanvas)
    print("Clean PDF with Diagrams generated successfully at:", filename)

if __name__ == "__main__":
    out_path = r"C:\Users\MOUAD\Desktop\ESP32-CAM-CAR-main\ESP32_CAM_Car_Documentation.pdf"
    build_pdf(out_path)

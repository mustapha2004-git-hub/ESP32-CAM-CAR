import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

os.makedirs("assets", exist_ok=True)

# -------------------------------------------------------------
# 1. SYSTEM ARCHITECTURE DIAGRAM
# -------------------------------------------------------------
def generate_system_architecture():
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 52)
    ax.axis('off')

    # Color palette
    c_esp_border = '#1E3A8A'
    c_esp_bg = '#EFF6FF'
    c_pc_border = '#0D9488'
    c_pc_bg = '#F0FDFA'
    c_motor_border = '#B45309'
    c_motor_bg = '#FFFBEB'
    c_power_border = '#DC2626'
    c_power_bg = '#FEF2F2'

    # Background Panels / Modules
    # 1. ESP32-CAM Box
    ax.add_patch(patches.FancyBboxPatch((2, 16), 34, 32, boxstyle="round,pad=0.8,rounding_size=1.5",
                                        facecolor=c_esp_bg, edgecolor=c_esp_border, linewidth=2))
    ax.text(19, 45.5, "ESP32-CAM (AI-Thinker)", fontsize=11, fontweight='bold', color=c_esp_border, ha='center')
    ax.text(19, 43, "Edge Acquisition & Actuation", fontsize=8, color='#475569', ha='center', style='italic')

    # Sub-blocks inside ESP32
    # Camera sensor
    ax.add_patch(patches.Rectangle((4, 33), 30, 8, facecolor='#DBEAFE', edgecolor='#3B82F6', linewidth=1))
    ax.text(19, 38, "OV5640 5MP Image Sensor", fontsize=9, fontweight='bold', color='#1E40AF', ha='center')
    ax.text(19, 35, "QVGA (320x240) @ 5 FPS | 10MHz XCLK", fontsize=7.5, color='#1E3A8A', ha='center')

    # Dual HTTP Servers
    ax.add_patch(patches.Rectangle((4, 23), 30, 8, facecolor='#DBEAFE', edgecolor='#3B82F6', linewidth=1))
    ax.text(19, 28, "Dual Asynchronous Web Daemons", fontsize=8.5, fontweight='bold', color='#1E40AF', ha='center')
    ax.text(19, 25, "Port 81: /stream (MJPEG) | Port 80: /action=CMD", fontsize=7.5, color='#1E3A8A', ha='center')

    # Watchdog & GPIO
    ax.add_patch(patches.Rectangle((4, 18), 30, 4, facecolor='#BFDBFE', edgecolor='#2563EB', linewidth=0.8))
    ax.text(19, 20, "Fail-Safe Watchdog (300ms) + Direction Pins (13,15,14,2)", fontsize=6.8, fontweight='bold', color='#1E3A8A', ha='center')

    # 2. PC Workstation Box
    ax.add_patch(patches.FancyBboxPatch((64, 16), 34, 32, boxstyle="round,pad=0.8,rounding_size=1.5",
                                        facecolor=c_pc_bg, edgecolor=c_pc_border, linewidth=2))
    ax.text(81, 45.5, "PC Workstation (Host)", fontsize=11, fontweight='bold', color=c_pc_border, ha='center')
    ax.text(81, 43, "Neural Perception & Decision Engine", fontsize=8, color='#475569', ha='center', style='italic')

    # Sub-blocks inside PC
    # Stream Ingestion Thread
    ax.add_patch(patches.Rectangle((66, 35), 30, 6.5, facecolor='#CCFBF1', edgecolor='#14B8A6', linewidth=1))
    ax.text(81, 39.5, "LatestFrame Stream Thread", fontsize=8.5, fontweight='bold', color='#0F766E', ha='center')
    ax.text(81, 37, "Zero-Buffer Unlagged Ingestion via Requests", fontsize=7.2, color='#115E59', ha='center')

    # YOLOv8 + ArUco
    ax.add_patch(patches.Rectangle((66, 26.5), 30, 7.5, facecolor='#CCFBF1', edgecolor='#14B8A6', linewidth=1))
    ax.text(81, 31.5, "Vision Core: YOLOv8n + ArUco", fontsize=8.5, fontweight='bold', color='#0F766E', ha='center')
    ax.text(81, 28.5, "Tri-Zone Slicing (L / C / R) & Goal Centroid Tracking", fontsize=7.2, color='#115E59', ha='center')

    # Finite State Machine + Smoothing
    ax.add_patch(patches.Rectangle((66, 18), 30, 7.5, facecolor='#CCFBF1', edgecolor='#14B8A6', linewidth=1))
    ax.text(81, 23, "FSM & Asymmetric Smoother", fontsize=8.5, fontweight='bold', color='#0F766E', ha='center')
    ax.text(81, 20, "States: AVOID, ALIGN, GO, ARRIVED | 0ms Stop Bypass", fontsize=7.2, color='#115E59', ha='center')

    # 3. Actuation Subsystem Box (Below ESP32)
    ax.add_patch(patches.FancyBboxPatch((2, 1), 48, 12.5, boxstyle="round,pad=0.6,rounding_size=1.2",
                                        facecolor=c_motor_bg, edgecolor=c_motor_border, linewidth=1.5))
    ax.text(26, 10.5, "Actuation: L298N H-Bridge & DC Gearmotors", fontsize=9, fontweight='bold', color=c_motor_border, ha='center')
    
    # Motor driver details
    ax.add_patch(patches.Rectangle((4, 2.5), 20, 6.5, facecolor='#FDE68A', edgecolor='#D97706', linewidth=0.8))
    ax.text(14, 6.8, "Left TT Motor", fontsize=8, fontweight='bold', color='#92400E', ha='center')
    ax.text(14, 4.2, "IN1 (13), IN2 (15) -> OUT1/2", fontsize=7, color='#78350F', ha='center')

    ax.add_patch(patches.Rectangle((28, 2.5), 20, 6.5, facecolor='#FDE68A', edgecolor='#D97706', linewidth=0.8))
    ax.text(38, 6.8, "Right TT Motor", fontsize=8, fontweight='bold', color='#92400E', ha='center')
    ax.text(38, 4.2, "IN3 (14), IN4 (2) -> OUT3/4", fontsize=7, color='#78350F', ha='center')

    # 4. Power Subsystem Box
    ax.add_patch(patches.FancyBboxPatch((55, 1), 43, 12.5, boxstyle="round,pad=0.6,rounding_size=1.2",
                                        facecolor=c_power_bg, edgecolor=c_power_border, linewidth=1.5))
    ax.text(76.5, 10.5, "Dual Isolated Power Architecture", fontsize=9, fontweight='bold', color=c_power_border, ha='center')
    ax.text(76.5, 7.2, "Logic: 3.7V Li-ion -> MT3608 Boost (5.0V) + 470uF Cap", fontsize=7.5, color='#991B1B', ha='center')
    ax.text(76.5, 4.2, "Motors: 6.5V Dedicated Battery -> L298N (Common Ground)", fontsize=7.5, color='#991B1B', ha='center')

    # Connecting Arrows
    # Video Stream Arrow (ESP32 -> PC)
    ax.annotate('', xy=(64, 38), xytext=(36, 38),
                arrowprops=dict(facecolor='#2563EB', edgecolor='#1D4ED8', width=2.5, headwidth=8, headlength=8))
    ax.text(50, 40, "Wi-Fi MJPEG Stream (:81/stream)\nQVGA @ 5 FPS", fontsize=7.5, fontweight='bold', color='#1E40AF', ha='center')

    # Command Telemetry Arrow (PC -> ESP32)
    ax.annotate('', xy=(36, 25), xytext=(64, 25),
                arrowprops=dict(facecolor='#059669', edgecolor='#047857', width=2.5, headwidth=8, headlength=8))
    ax.text(50, 26.5, "HTTP GET /action=CMD&ai=1 (:80)\n[F, B, L, R, S] Heartbeat 120ms", fontsize=7.5, fontweight='bold', color='#065F46', ha='center')

    # ESP32 -> L298N Arrow
    ax.annotate('', xy=(20, 13.5), xytext=(20, 16),
                arrowprops=dict(facecolor='#B45309', edgecolor='#92400E', width=2, headwidth=6, headlength=6))
    ax.text(26, 14.5, "GPIO 13, 15, 14, 2", fontsize=7, fontweight='bold', color='#92400E')

    plt.tight_layout()
    plt.savefig("assets/system_architecture.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated: assets/system_architecture.png")


# -------------------------------------------------------------
# 2. ELECTRICAL WIRING SCHEMATIC DIAGRAM
# -------------------------------------------------------------
def generate_wiring_schematic():
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 55)
    ax.axis('off')

    # Central Components
    # ESP32-CAM module (Left side)
    ax.add_patch(patches.FancyBboxPatch((5, 16), 26, 34, boxstyle="round,pad=0.5,rounding_size=1.2",
                                        facecolor='#1E293B', edgecolor='#0EA5E9', linewidth=2))
    ax.text(18, 47, "ESP32-CAM", fontsize=11, fontweight='bold', color='white', ha='center')
    ax.text(18, 44.5, "(AI-Thinker Board)", fontsize=8, color='#94A3B8', ha='center')

    # Pins on ESP32-CAM
    esp_pins = [
        (40, "5V (Power In)"),
        (35, "GND (Ground)"),
        (30, "GPIO 13 (IN1)"),
        (25, "GPIO 15 (IN2)"),
        (20, "GPIO 14 (IN3)"),
        (15, "GPIO 2  (IN4)")
    ]
    for y_pos, label in esp_pins:
        ax.add_patch(patches.Circle((31, y_pos), 1.0, facecolor='#38BDF8', edgecolor='white', linewidth=1))
        ax.text(29, y_pos-0.7, label, fontsize=7.2, color='white', ha='right', fontweight='bold')

    # L298N Driver (Center Right)
    ax.add_patch(patches.FancyBboxPatch((48, 14), 28, 38, boxstyle="round,pad=0.5,rounding_size=1.2",
                                        facecolor='#78350F', edgecolor='#F59E0B', linewidth=2))
    ax.text(62, 49, "L298N Motor Driver", fontsize=11, fontweight='bold', color='white', ha='center')
    ax.text(62, 46.5, "Dual Full-Bridge Module", fontsize=8, color='#FDE68A', ha='center')

    # Pins on L298N (Left side inputs)
    l298_inputs = [
        (30, "IN1"),
        (25, "IN2"),
        (20, "IN3"),
        (15, "IN4"),
    ]
    for y_pos, label in l298_inputs:
        ax.add_patch(patches.Circle((48, y_pos), 1.0, facecolor='#FBBF24', edgecolor='black', linewidth=0.8))
        ax.text(50.5, y_pos-0.7, label, fontsize=7.5, color='white', fontweight='bold')

    # Power terminals on L298N (Bottom)
    ax.add_patch(patches.Circle((53, 17), 1.1, facecolor='#EF4444', edgecolor='white', linewidth=1))
    ax.text(53, 19, "+12V", fontsize=7.2, color='#FCA5A5', ha='center', fontweight='bold')

    ax.add_patch(patches.Circle((62, 17), 1.1, facecolor='#0284C7', edgecolor='white', linewidth=1))
    ax.text(62, 19, "GND", fontsize=7.2, color='#BAE6FD', ha='center', fontweight='bold')

    # Motor Terminals on L298N (Right side outputs)
    ax.add_patch(patches.Circle((76, 38), 1.0, facecolor='#10B981', edgecolor='white', linewidth=1))
    ax.text(74, 37.3, "OUT1/2", fontsize=7.2, color='#A7F3D0', ha='right', fontweight='bold')

    ax.add_patch(patches.Circle((76, 25), 1.0, facecolor='#10B981', edgecolor='white', linewidth=1))
    ax.text(74, 24.3, "OUT3/4", fontsize=7.2, color='#A7F3D0', ha='right', fontweight='bold')

    # Connect Control Lines (ESP32 to L298N)
    colors_ctrl = ['#F97316', '#EAB308', '#06B6D4', '#8B5CF6']
    for idx, (y_pos, _) in enumerate(l298_inputs):
        ax.plot([31, 48], [y_pos, y_pos], color=colors_ctrl[idx], linewidth=1.8)

    # Motors (Far Right)
    # Left Motor
    ax.add_patch(patches.FancyBboxPatch((85, 34), 13, 10, boxstyle="round,pad=0.4", facecolor='#F3F4F6', edgecolor='#4B5563', linewidth=1.5))
    ax.text(91.5, 41, "Left Motor", fontsize=8.5, fontweight='bold', color='#111827', ha='center')
    ax.text(91.5, 37, "TT Gearbox", fontsize=7, color='#4B5563', ha='center')
    ax.plot([76, 85], [38, 38], color='#059669', linewidth=2)

    # Right Motor
    ax.add_patch(patches.FancyBboxPatch((85, 20), 13, 10, boxstyle="round,pad=0.4", facecolor='#F3F4F6', edgecolor='#4B5563', linewidth=1.5))
    ax.text(91.5, 27, "Right Motor", fontsize=8.5, fontweight='bold', color='#111827', ha='center')
    ax.text(91.5, 23, "TT Gearbox", fontsize=7, color='#4B5563', ha='center')
    ax.plot([76, 85], [25, 25], color='#059669', linewidth=2)

    # Power Source 1: Motor Battery 6.5V (Bottom Center)
    ax.add_patch(patches.Rectangle((46, 2), 22, 8, facecolor='#FEF2F2', edgecolor='#DC2626', linewidth=1.5))
    ax.text(57, 7, "Motor Battery (6.5V)", fontsize=8, fontweight='bold', color='#991B1B', ha='center')
    ax.text(57, 4.2, "Independent High-Drain", fontsize=7, color='#B91C1C', ha='center')

    # Lines from Motor Battery to L298N
    # Positive (Red)
    ax.plot([52, 52, 53], [10, 14, 17], color='#DC2626', linewidth=2.2)
    # Negative (Blue/Black)
    ax.plot([62, 62], [10, 17], color='#0284C7', linewidth=2.2)

    # Power Source 2: Logic Supply (Bottom Left)
    ax.add_patch(patches.Rectangle((4, 2), 28, 8, facecolor='#EFF6FF', edgecolor='#2563EB', linewidth=1.5))
    ax.text(18, 7, "Logic: 3.7V Li-ion + Step-Up", fontsize=8, fontweight='bold', color='#1E40AF', ha='center')
    ax.text(18, 4.2, "Outputs Regulated +5.0V", fontsize=7, color='#1E3A8A', ha='center')

    # Line from Boost to ESP32 5V
    ax.plot([8, 8, 31], [10, 40, 40], color='#DC2626', linewidth=2.2)
    ax.text(6, 27, "+5.0V", fontsize=7.5, fontweight='bold', color='#DC2626', rotation=90)

    # Line from Boost GND to ESP32 GND
    ax.plot([14, 14, 31], [10, 35, 35], color='#0284C7', linewidth=2.2)
    ax.text(12, 27, "GND", fontsize=7.5, fontweight='bold', color='#0284C7', rotation=90)

    # Common GND bridge between ESP32 and L298N
    ax.plot([31, 38, 38, 62], [35, 35, 17, 17], color='#0284C7', linewidth=2.2, linestyle='--')
    ax.text(42, 27, "COMMON GND (MANDATORY)", fontsize=6.8, fontweight='bold', color='#0284C7', rotation=90)

    # 470uF Capacitor callout
    ax.add_patch(patches.Circle((20, 37.5), 1.8, facecolor='#F3F4F6', edgecolor='#374151', linewidth=1.2))
    ax.text(20, 37, "470µF", fontsize=6, fontweight='bold', color='#111827', ha='center')
    ax.text(20, 41, "Decoupling Cap", fontsize=6.5, color='#374151', ha='center', fontweight='bold')

    # Labels for Jumpers & Warnings
    ax.text(62, 40, "ENA/ENB Jumpers ON\n(Fixed Full Speed)", fontsize=7, color='#FEF3C7', ha='center', style='italic')

    plt.tight_layout()
    plt.savefig("assets/wiring_schematic.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated: assets/wiring_schematic.png")

if __name__ == "__main__":
    generate_system_architecture()
    generate_wiring_schematic()

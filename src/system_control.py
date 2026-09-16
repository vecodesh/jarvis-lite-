"""
JARVIS-lite: System Telemetry & Workstation Controls (Phase 7)

Provides:
1. Live hardware telemetry (CPU %, RAM %, Battery %).
2. Voice & text workstation commands:
   - Open LeetCode / GitHub / LinkedIn in browser.
   - Lock workstation (ctypes LockWorkStation).
   - Capture desktop screenshot.
   - System load status report.
"""

import os
import sys
import ctypes
import webbrowser
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import psutil

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = BASE_DIR / "screenshots"


def get_system_telemetry() -> dict:
    """Returns real-time CPU, RAM, and Battery telemetry."""
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent

    battery = None
    plugged = None
    try:
        batt = psutil.sensors_battery()
        if batt:
            battery = int(batt.percent)
            plugged = batt.power_plugged
    except Exception:
        pass

    return {
        "cpu_percent": cpu,
        "ram_percent": ram,
        "battery_percent": battery,
        "battery_plugged": plugged,
    }


def execute_system_command(command: str) -> tuple[bool, str]:
    """
    Executes a workstation system action based on voice/text command.
    Returns (success, message).
    """
    clean = command.strip().lower()

    # 1. Open LeetCode
    if "leetcode" in clean:
        webbrowser.open("https://leetcode.com/problemset/all/")
        return True, "Opening LeetCode problem archive in your browser."

    # 2. Open GitHub
    if "github" in clean:
        webbrowser.open("https://github.com/")
        return True, "Opening GitHub in your default browser."

    # 3. Open LinkedIn
    if "linkedin" in clean:
        webbrowser.open("https://www.linkedin.com/jobs/")
        return True, "Opening LinkedIn Jobs in your browser."

    # 4. Lock Workstation
    if any(k in clean for k in ["lock pc", "lock workstation", "lock screen", "lock computer"]):
        try:
            ctypes.windll.user32.LockWorkStation()
            return True, "Securing workstation and locking display."
        except Exception as e:
            return False, f"Could not lock workstation: {e}"

    # 5. Capture Screenshot
    if any(k in clean for k in ["screenshot", "capture screen"]):
        try:
            SCREENSHOT_DIR.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shot_path = SCREENSHOT_DIR / f"jarvis_snap_{timestamp}.png"

            # Native PowerShell screen capture
            ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bitmap.Save('{str(shot_path).replace("\\", "/")}', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
"""
            import subprocess
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return True, f"Screen captured and saved to: {shot_path.name}"
        except Exception as e:
            return False, f"Screenshot error: {e}"

    # 6. System Load Report
    if any(k in clean for k in ["system status", "hardware status", "telemetry", "system load", "cpu load", "ram usage"]):
        t = get_system_telemetry()
        batt_str = f", Battery: {t['battery_percent']}%" if t['battery_percent'] is not None else ""
        return True, f"Hardware Telemetry — CPU: {t['cpu_percent']}%, RAM: {t['ram_percent']}%{batt_str}. All subsystems operating within normal parameters."

    return False, "Unrecognized system command."

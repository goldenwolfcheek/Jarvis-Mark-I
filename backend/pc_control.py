"""PC Control — launch apps, control volume, type text, etc.

╔══════════════════════════════════════════════════════════════════════╗
║  CROSS-PLATFORM COMPATIBILITY                                      ║
║                                                                    ║
║  This module is currently **Windows-only**.  Every function uses   ║
║  PowerShell via subprocess to interact with the OS:                ║
║                                                                    ║
║    • launch_app()       → cmd.exe / shell=True                     ║
║    • set_volume()       → PowerShell (WMP OCX / SendKeys)          ║
║    • mute_audio()       → PowerShell SendKeys                      ║
║    • type_text()        → PowerShell SendKeys                      ║
║    • take_screenshot()  → PowerShell (WinForms)                    ║
║    • get_system_status()→ PowerShell (CIM/WMI)                     ║
║                                                                    ║
║  To port to Linux/macOS, each function would need an alternative   ║
║  implementation:                                                   ║
║    • App launching → subprocess.Popen with platform-appropriate    ║
║                      paths (e.g. `open` on macOS, `xdg-open` on   ║
║                      Linux).                                       ║
║    • Volume        → pactl/amixer (Linux), osascript (macOS).      ║
║    • Typing        → pyautogui or xdotool/xte (Linux),            ║
║                      AppleScript (macOS).                          ║
║    • Screenshots   → pyautogui or import (Linux), screencapture   ║
║                      (macOS).                                      ║
║    • System status → psutil (cross-platform library alternative).  ║
║                                                                    ║
║  Recommended approach for porting: wrap each function body in      ║
║  `if sys.platform == \"win32\": ... elif sys.platform == \"darwin\":  ║
║  ... else: ...` branching.                                         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import subprocess
import time


async def launch_app(command: str, args: str = "") -> dict:
    """Launch a Windows application.

    Args:
        command: The executable name or 'start' for URI protocol.
        args: Optional arguments or URI.

    Returns:
        dict with success status and message.
    """
    try:
        if command == "start" and args:
            # For URI protocols like discord://, steam://, spotify:
            full_cmd = f"start {args}"
            subprocess.Popen(full_cmd, shell=True)
        elif command:
            full_cmd = f"{command} {args}".strip()
            subprocess.Popen(full_cmd, shell=True)
        else:
            return {"success": False, "error": "No command specified"}

        return {"success": True, "message": f"Launched: {command} {args}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def set_volume(level: int) -> dict:
    """Set system volume (0-100). Uses nircmd if available, else PowerShell."""
    level = max(0, min(100, level))
    try:
        # Try PowerShell method (works on most Windows systems)
        ps_cmd = [
            "powershell",
            "-c",
            f"(New-Object -ComObject WScript.Shell).SendKeys([char]173)",
        ]
        # Actually, let's use the proper Windows audio API via PowerShell
        ps_script = f"""
        $obj = New-Object -ComObject 'WMPlayer.OCX.7'
        $settings = $obj.settings
        $settings.volume = {level}
        """.strip()
        subprocess.run(
            ["powershell", "-c", ps_script],
            capture_output=True,
            timeout=5,
        )
        return {"success": True, "message": f"Volume set to {level}%"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def mute_audio(mute: bool = True) -> dict:
    """Mute or unmute system audio."""
    try:
        key = "{173}" if mute else "{174}"  # WM_APPCOMMAND volume mute toggle
        ps_cmd = [
            "powershell",
            "-c",
            f"(New-Object -ComObject WScript.Shell).SendKeys('{key}')",
        ]
        subprocess.run(ps_cmd, capture_output=True, timeout=5)
        return {"success": True, "message": "Audio muted" if mute else "Audio unmuted"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def type_text(text: str) -> dict:
    """Type text using keyboard simulation."""
    try:
        # Escape special characters for PowerShell SendKeys
        safe = (
            text.replace("{", "{{}")
            .replace("}", "}}")
            .replace("~", "{~}")
            .replace("%", "{%}")
            .replace("^", "{^}")
            .replace("+", "{+}")
        )
        ps_cmd = [
            "powershell",
            "-c",
            f"(New-Object -ComObject WScript.Shell).SendKeys('{safe}')",
        ]
        subprocess.run(ps_cmd, capture_output=True, timeout=10)
        return {"success": True, "message": f"Typed: {text[:50]}..."}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def take_screenshot(save_path: str = None) -> dict:
    """Capture a screenshot."""
    try:
        if not save_path:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            save_path = os.path.expanduser(f"~/.jarvis/screenshots/{timestamp}.png")
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.X, $screen.Y, 0, 0, $bitmap.Size)
        $bitmap.Save('{save_path}')
        $graphics.Dispose()
        $bitmap.Dispose()
        """
        subprocess.run(
            ["powershell", "-c", ps_script],
            capture_output=True,
            timeout=15,
        )
        return {"success": True, "path": save_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_system_status() -> dict:
    """Get basic system status info."""
    try:
        # CPU usage
        cpu = subprocess.run(
            [
                "powershell",
                "-c",
                "Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select -ExpandProperty Average",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        cpu_pct = cpu.stdout.strip() or "N/A"

        # Memory
        mem = subprocess.run(
            [
                "powershell",
                "-c",
                "$os = Get-CimInstance Win32_OperatingSystem; [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize * 100)",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        mem_pct = mem.stdout.strip() or "N/A"

        return {
            "success": True,
            "cpu_percent": cpu_pct,
            "memory_percent": mem_pct,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

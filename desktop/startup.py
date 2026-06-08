"""
Auto-start — register Jarvis server to launch on Windows startup.

Uses the Windows Startup folder via a VBScript launcher (no console window).
The VBS launcher runs run_server.py directly using wscript.exe.
"""

import logging
import os
import subprocess
import sys
import shutil

logger = logging.getLogger("jarvis.startup")

# Paths
JARVIS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Windows Startup folder
STARTUP_FOLDER = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "Microsoft", "Windows", "Start Menu", "Programs", "Startup",
)

SHORTCUT_NAME = "Jarvis Mark 1.lnk"
VBS_FILENAME = "Jarvis Mark 1.vbs"
VBS_PROJECT_FILENAME = "start_jarvis_boot.vbs"


def get_python_exe() -> str:
    """Get the Python executable path, preferring the current venv."""
    if sys.executable and "venv" in sys.executable.lower():
        return sys.executable
    # Try common names
    for name in ["python", "python3", "py"]:
        try:
            result = subprocess.run(
                [name, "--version"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return name
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return sys.executable or "python"


def is_registered() -> bool:
    """Check if Jarvis is registered for auto-start."""
    shortcut_path = os.path.join(STARTUP_FOLDER, SHORTCUT_NAME)
    vbs_path = os.path.join(STARTUP_FOLDER, VBS_FILENAME)
    return os.path.exists(shortcut_path) or os.path.exists(vbs_path)


def register() -> dict:
    """Register Jarvis server to auto-start on Windows login."""
    try:
        python_exe = get_python_exe()
        server_script = os.path.join(JARVIS_ROOT, "run_server.py")

        # Create a VBS launcher script in the project folder
        # This runs the Python server with no console window
        vbs_lines = [
            "' Jarvis Mark 1 - Auto-start launcher",
            "Dim shell",
            "Set shell = CreateObject(\"WScript.Shell\")",
            'shell.Run "\"' + python_exe + '\" \"' + server_script + '\"", 0, False',
            "Set shell = Nothing",
        ]
        vbs_path = os.path.join(JARVIS_ROOT, VBS_PROJECT_FILENAME)
        with open(vbs_path, "w") as f:
            f.write("\r\n".join(vbs_lines) + "\r\n")

        # Create shortcut in Startup folder using PowerShell
        ps_script = (
            '$s = New-Object -ComObject WScript.Shell;'
            '$c = $s.CreateShortcut("' + STARTUP_FOLDER + '\\' + SHORTCUT_NAME + '");'
            '$c.TargetPath = "wscript.exe";'
            '$c.Arguments = "' + vbs_path + '";'
            '$c.WorkingDirectory = "' + JARVIS_ROOT + '";'
            '$c.Description = "Jarvis Mark 1 - AI Desktop Assistant";'
            '$c.Save()'
        )

        result = subprocess.run(
            ["powershell", "-c", ps_script],
            capture_output=True, text=True, timeout=15,
        )

        if result.returncode != 0:
            # Fallback: copy the VBS directly to Startup folder
            fallback_path = os.path.join(STARTUP_FOLDER, VBS_FILENAME)
            shutil.copy2(vbs_path, fallback_path)
            logger.info(f"PowerShell failed, copied VBS directly to Startup folder: {fallback_path}")

        return {"success": True, "message": "Jarvis registered to start on boot"}
    except Exception as e:
        logger.exception("Failed to register auto-start")
        return {"success": False, "error": str(e)}


def unregister() -> dict:
    """Remove Jarvis from auto-start."""
    try:
        shortcut_path = os.path.join(STARTUP_FOLDER, SHORTCUT_NAME)
        vbs_startup_path = os.path.join(STARTUP_FOLDER, VBS_FILENAME)

        for p in [shortcut_path, vbs_startup_path]:
            if os.path.exists(p):
                os.remove(p)

        return {"success": True, "message": "Jarvis removed from auto-start"}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "register":
        result = register()
        print(result["message"])
    elif action == "unregister":
        result = unregister()
        print(result["message"])
    else:
        if is_registered():
            print("Jarvis is registered to start on boot")
        else:
            print("Jarvis is NOT registered for auto-start")

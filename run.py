#!/usr/bin/env python3
"""
Jarvis Mark 1 — Entry Point

Launcher that:
  1. Installs dependencies (first run only)
  2. Starts the backend server
  3. Opens the Jarvis desktop window (or browser)
"""

import os
import subprocess
import sys
import webbrowser

JARVIS_ROOT = os.path.dirname(os.path.abspath(__file__))

def check_deps():
    """Check if core dependencies are installed."""
    try:
        import fastapi  # noqa
        import uvicorn  # noqa
        import edge_tts  # noqa
        return True
    except ImportError:
        return False


def install_deps():
    """Install required Python packages."""
    print("🔧 Installing Jarvis dependencies...")
    req = os.path.join(JARVIS_ROOT, "backend", "requirements.txt")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("✅ Dependencies installed")
        return True
    else:
        print("❌ Failed to install dependencies:")
        print(result.stderr)
        return False


def main():
    print("""
    ╔══════════════════════════════════╗
    ║        J.A.R.V.I.S. Mark 1       ║
    ║  Just A Rather Very Intelligent  ║
    ║           System                 ║
    ╚══════════════════════════════════╝
    """)

    # Check and install dependencies
    if not check_deps():
        if not install_deps():
            sys.exit(1)

    # Change to project root
    os.chdir(JARVIS_ROOT)
    sys.path.insert(0, JARVIS_ROOT)

    # Try pywebview first, fall back to browser
    try:
        import webview  # noqa
        from desktop.main import main as desktop_main
        desktop_main()
    except ImportError:
        print("🌐 Starting web server (browser mode)...")
        print("   Open http://127.0.0.1:9119 in your browser")
        print("   Press Ctrl+C to stop\n")

        from backend.server import run_server
        run_server()


if __name__ == "__main__":
    main()

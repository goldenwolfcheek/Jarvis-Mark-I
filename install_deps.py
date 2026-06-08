"""Jarvis Mark 1 — One-time dependency installer."""

import os
import subprocess
import sys

JARVIS_ROOT = os.path.dirname(os.path.abspath(__file__))


def install():
    """Install all required dependencies."""
    print("=" * 60)
    print("  J.A.R.V.I.S. Mark 1 — Dependency Installer")
    print("=" * 60)

    # Step 1: Install Python packages
    print("\n📦 Installing Python packages...")
    req = os.path.join(JARVIS_ROOT, "backend", "requirements.txt")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("❌ Failed:", result.stderr)
        return False
    print("✅ Python packages installed")

    # Step 2: Install pywebview (desktop window)
    print("\n📦 Installing desktop support (pywebview)...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "pywebview"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("✅ pywebview installed")
    else:
        print("⚠️  pywebview not installed (will use browser mode)")

    # Step 3: Optional speech-to-text
    print("\n📦 Installing optional speech-to-text (faster-whisper)...")
    print("   (This may take a few minutes)")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "faster-whisper"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("✅ faster-whisper installed")
    else:
        print("⚠️  faster-whisper not installed (voice input unavailable)")

    print("\n" + "=" * 60)
    print("  ✅ Installation complete!")
    print("  Run 'python run.py' to start Jarvis")
    print("=" * 60)
    return True


if __name__ == "__main__":
    install()

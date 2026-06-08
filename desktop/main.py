"""Jarvis Desktop — pywebview wrapper.

Launches the Jarvis backend server in a background thread,
then opens a native desktop window with the Jarvis UI.
"""

import logging
import os
import sys
import threading

logger = logging.getLogger("jarvis.desktop")

# Add parent dir to path so `from backend import ...` works
JARVIS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if JARVIS_ROOT not in sys.path:
    sys.path.insert(0, JARVIS_ROOT)

HOST = "127.0.0.1"
PORT = 9119


def _start_server():
    """Run the backend server in a background thread."""
    from backend.server import run_server
    run_server(host=HOST, port=PORT)


def _wait_for_server(timeout: int = 15) -> bool:
    """Wait until the backend server is ready."""
    import time
    import urllib.request

    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(f"http://{HOST}:{PORT}/api/status", timeout=2)
            if resp.status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def open_desktop_window(title: str = "JARVIS Mark 1"):
    """Open a native desktop window with the Jarvis UI."""
    # Try importing webview; if not available, open browser
    try:
        import webview

        window = webview.create_window(
            title=title,
            url=f"http://{HOST}:{PORT}",
            width=1200,
            height=800,
            resizable=True,
            fullscreen=False,
            min_size=(800, 500),
            confirm_close=False,
        )
        webview.start(
            private_mode_off=True,  # allow localStorage to persist
            storage_path=os.path.expanduser("~/.jarvis/webview"),
        )
    except ImportError:
        logger.warning("pywebview not installed. Opening in browser instead.")
        import webbrowser
        webbrowser.open(f"http://{HOST}:{PORT}")
        # Keep the process alive
        import time
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


def main():
    """Start Jarvis as a desktop application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("Jarvis Mark 1 — Desktop mode")

    # Start server in background
    server_thread = threading.Thread(target=_start_server, daemon=True)
    server_thread.start()

    # Wait for server to be ready
    if not _wait_for_server():
        logger.error("Backend server failed to start. Check logs.")
        sys.exit(1)

    logger.info(f"Backend ready at http://{HOST}:{PORT}")

    # Open desktop window
    open_desktop_window()


if __name__ == "__main__":
    main()

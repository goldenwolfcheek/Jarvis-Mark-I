"""Jarvis Mark 1 — Entry point.

Usage:
    python -m backend         # Start the server
    python -m backend --port 9119   # Custom port
"""

import sys


def main():
    """Parse args and start the Jarvis server."""
    port = 9119
    host = "127.0.0.1"

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
        if arg == "--host" and i + 1 < len(args):
            host = args[i + 1]

    from backend.server import run_server

    run_server(host=host, port=port)


if __name__ == "__main__":
    main()

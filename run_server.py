"""Launcher — starts Jarvis Mark 1 server.

Jarvis manages its own provider configuration independently of Hermes.
Uses the system Python (works with any Python 3.8+ that has deps installed).
"""

import sys, os

# Make sure the project root is on sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.server import run_server
run_server()

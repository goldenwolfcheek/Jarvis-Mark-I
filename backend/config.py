"""Jarvis configuration — stores settings, registered apps, and user prefs."""

import json
import os
from pathlib import Path

# Where Jarvis stores its data
JARVIS_HOME = Path(os.environ.get("JARVIS_HOME", Path.home() / ".jarvis"))
JARVIS_HOME.mkdir(parents=True, exist_ok=True)

# Path to Hermes agent source (for importing AIAgent)
# NOTE: The default path below is Windows-specific (AppData\Local\hermes\...).
# On macOS it would typically be ~/Library/Application Support/hermes/hermes-agent,
# and on Linux ~/.local/share/hermes/hermes-agent.
# Set the HERMES_SOURCE environment variable to override.
HERMES_SOURCE = Path(
    os.environ.get(
        "HERMES_SOURCE",
        Path.home() / "AppData" / "Local" / "hermes" / "hermes-agent",
    )
)

CONFIG_FILE = JARVIS_HOME / "config.json"
APPS_FILE = JARVIS_HOME / "registered_apps.json"

DEFAULT_CONFIG = {
    "model": "deepseek-v4-flash-free",
    "provider": "opencode-zen",
    "base_url": "https://opencode.ai/zen/v1",
    "api_key": None,
    "tts_enabled": True,
    "tts_provider": "edge",
    "auto_speak": True,
    "stt_enabled": True,
    "stt_provider": "local",
    "volume": 80,
    "theme": "dark",
    "start_on_boot": False,
}


def load_config() -> dict:
    """Load Jarvis config, merging with defaults."""
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text("utf-8"))
            cfg.update(data)
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict) -> None:
    """Save Jarvis config."""
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    CONFIG_FILE.write_text(json.dumps(merged, indent=2), "utf-8")


def load_registered_apps() -> list[dict]:
    """Load the list of user-registered apps."""
    if APPS_FILE.exists():
        try:
            return json.loads(APPS_FILE.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return _default_apps()


def save_registered_apps(apps: list[dict]) -> None:
    """Save the list of registered apps."""
    APPS_FILE.write_text(json.dumps(apps, indent=2), "utf-8")


def _default_apps() -> list[dict]:
    """Default app registry for a Windows PC."""
    return [
        {"name": "Default Web Browser", "command": "start", "args": ""},
        {"name": "Discord", "command": "start", "args": "discord://"},
        {"name": "Notepad", "command": "notepad", "args": ""},
        {"name": "Spotify", "command": "start", "args": "spotify:"},
        {"name": "Steam", "command": "start", "args": "steam://"},
        {"name": "VS Code", "command": "code", "args": ""},
        {"name": "File Explorer", "command": "explorer", "args": ""},
        {"name": "Task Manager", "command": "taskmgr", "args": ""},
        {"name": "Command Prompt", "command": "cmd", "args": ""},
        {"name": "Calculator", "command": "calc", "args": ""},
        {"name": "Calendar", "command": "start", "args": "outlookcal:"},
    ]

# Cross-Platform Compatibility Analysis
## Jarvis Mark 1 — Linux & macOS Migration Guide

**Last updated:** June 08, 2026  
**Project root:** `I:\Code Shit\OpenCode\Projects\Jarvis Mark 1\`

---

## Executive Summary

Jarvis Mark 1 is currently **Windows-only** due to three components that rely heavily on Windows-specific APIs (PowerShell, VBScript, the Windows Startup folder, and hardcoded `C:\Program Files\` paths). The **core logic** — FastAPI server, AI agent, file operations, web search/fetch, configuration, and the entire frontend — is already fully cross-platform. Roughly **60% of the codebase** works without changes on Linux and macOS.

Porting Jarvis to full cross-platform support requires:

- **Rewriting `backend/pc_control.py`** (~192 lines) with per-OS branching — the largest single effort.
- **Replacing `desktop/startup.py`** with a cross-platform auto-start mechanism.
- **Adding platform-aware paths** in `backend/tools.py` and `backend/config.py`.
- **Creating shell launchers** for Linux/macOS to replace the `.bat` and `.vbs` files.

With a phased approach, the core server can work on all platforms in **Phase 1** with no changes to the existing Windows code path, and full OS-level control (volume, typing, screenshots) can be added in **Phase 2** via optional `pyautogui` / `psutil` dependencies.

---

## ✅ Components That Work Cross-Platform (No Changes Needed)

These modules use only Python standard library or cross-platform third-party packages and function identically on Windows, macOS, and Linux.

| Module | File | Cross-Platform Since |
|--------|------|---------------------|
| **Server** | `backend/server.py` (869 lines) | FastAPI + uvicorn are fully cross-platform. Static file serving, WebSocket chat, TTS (edge-tts), STT (faster-whisper), and all REST API endpoints work on all three OSes. CORS origins use `localhost`/`127.0.0.1` — no OS dependency. |
| **Agent** | `backend/agent.py` (331 lines) | Uses only `urllib` (Python stdlib), `json`, and `logging`. Makes OpenAI-compatible API calls. No OS-specific code whatsoever. Already documented as "fully cross-platform." |
| **Tools (partial)** | `backend/tools.py` (543 lines) | `create_file`, `read_file`, `web_fetch`, `web_search`, `list_apps`, `execute_command`, `parse_xml_tool_calls`, `strip_xml_tool_calls`, and the entire tool registry/dispatch system are all pure Python with no OS dependencies. |
| **Config (core)** | `backend/config.py` (90 lines) | `JARVIS_HOME` uses `Path.home() / ".jarvis"` — a cross-platform convention. JSON config read/write is pure Python. The config defaults (model, provider, TTS/STT settings) are OS-agnostic. |
| **Frontend** | `frontend/index.html` (1970 lines) | Pure HTML5, CSS3, and JavaScript. Uses WebSocket to communicate with the backend. The Three.js 3D sphere, chat UI, settings panel, and voice recording all work in any modern browser on any platform. |
| **Launcher** | `run_server.py` (15 lines) | Just imports and calls `run_server()`. No OS-specific code. |
| **Dependencies** | `backend/requirements.txt` | `fastapi`, `uvicorn`, `websockets`, `edge-tts`, `python-multipart` — all available on PyPI and work on Windows, macOS, and Linux. Optional `faster-whisper` and `pywebview` are also cross-platform. |

---

## ❌ Components That Are Windows-Only

These modules will not function on Linux or macOS in their current form.

### 1. `backend/pc_control.py` (192 lines) — ⚠️ HIGH EFFORT

**Status:** 100% Windows-only. Every function shells out to `powershell -c ...`.

| Function | Windows Implementation | What Needs to Change |
|----------|----------------------|---------------------|
| `launch_app(command, args)` | `subprocess.Popen(full_cmd, shell=True)` with `start` for URI protocols (`discord://`, `steam://`, `spotify:`) | Add platform branching: `open` on macOS, `xdg-open` on Linux. URI protocol handling is already non-trivial on Windows; macOS handles `open discord://` natively, Linux needs `xdg-open discord://`. `shell=True` should be avoided where possible. |
| `set_volume(level)` | PowerShell `WMPlayer.OCX.7` COM object to set volume 0–100 | Replace with: **macOS** → `osascript -e "set volume output volume X"`; **Linux** → `pactl set-sink-volume @DEFAULT_SINK@ X%` or `amixer`. |
| `mute_audio(mute)` | PowerShell SendKeys `{173}` / `{174}` (virtual key codes) | Replace with: **macOS** → `osascript -e "set volume output muted (true/false)"`; **Linux** → `pactl set-sink-mute @DEFAULT_SINK@ toggle`. |
| `type_text(text)` | PowerShell `SendKeys()` via WScript.Shell COM object | Replace with **cross-platform**: `pyautogui.typewrite(text)` (best option — works on all 3 OSes). Or per-OS: **macOS** → `osascript -e 'tell app "System Events" to keystroke "..."'`; **Linux** → `xdotool type "..."` or `ydotool`. |
| `take_screenshot(save_path)` | PowerShell `System.Windows.Forms` / `System.Drawing` to capture screen | Replace with **cross-platform**: `pyautogui.screenshot()` (works on all 3 OSes, adds `pyautogui` dependency). Or per-OS: **macOS** → `screencapture`; **Linux** → `import` from ImageMagick or `gnome-screenshot`. |
| `get_system_status()` | PowerShell `Get-CimInstance Win32_Processor` (CPU) and `Win32_OperatingSystem` (memory) | Replace with **cross-platform**: `psutil.cpu_percent()` and `psutil.virtual_memory().percent` (adds `psutil` dependency — recommended). Return format should stay identical. |

#### Effort Estimate: **High** (2–3 days)
- Rewriting each function with `if sys.platform` branching.
- Adding `pyautogui` and `psutil` as optional dependencies.
- Testing on all three platforms.
- The `launch_app` URI protocol handling is especially tricky — Windows `start` is not equivalent to macOS `open` or Linux `xdg-open` for all URI schemes.

#### Recommended Alternatives
| Dependency | Cross-Platform | Notes |
|-----------|---------------|-------|
| `pyautogui` | ✅ macOS, Windows, Linux | Handles screenshot, typing, mouse control. Adds ~50KB. |
| `psutil` | ✅ macOS, Windows, Linux | Handles CPU, memory, disk, network, processes. Industry standard. |
| `pydub` + `pulsectl` / `pyobjc` | Partial | For Linux/macOS audio control (optional, niche). |

---

### 2. `desktop/startup.py` (129 lines) — ⚠️ MEDIUM EFFORT

**Status:** 100% Windows-only. Handles registering Jarvis to auto-start on user login.

| Aspect | Windows Implementation | What Needs to Change |
|--------|----------------------|---------------------|
| **Startup folder path** | `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` | **macOS**: `~/Library/LaunchAgents/` (plist files); **Linux**: `~/.config/autostart/` (`.desktop` files) or `~/.config/systemd/user/` (systemd user units). |
| **Launcher mechanism** | VBScript (`WScript.Shell.Run`) + PowerShell to create `.lnk` shortcut | **macOS**: Create a `.plist` file in `~/Library/LaunchAgents/`; **Linux**: Create a `.desktop` file in `~/.config/autostart/`. Both are simpler than the current Windows approach. |
| **Startup artifact** | VBS file + `.lnk` shortcut + `start_jarvis_boot.vbs` in project root | No intermediate VBS needed on Unix — just the autostart config file directly. |
| **python_exe detection** | Checks `sys.executable` for "venv" in path, falls back to `python`, `python3`, `py` | Already mostly cross-platform (just remove `py` as a fallback). |

#### Effort Estimate: **Medium** (1 day)
- `register()` needs to write a `.plist` or `.desktop` file instead of VBS + PowerShell.
- `unregister()` needs to remove those files.
- `is_registered()` needs to check existence of the correct file.
- The VBS launcher (`start_jarvis_boot.vbs`) becomes unnecessary on Unix.
- All three functions can have a clean `if sys.platform` structure.

---

### 3. `start_jarvis.bat` (25 lines) — ⚠️ LOW EFFORT

**Status:** Windows batch file. Checks for Python availability, then runs `python run.py`.

**What to create:** Equivalent shell launchers:

| Platform | File | Content |
|----------|------|---------|
| **Linux** | `start_jarvis.sh` | `#!/usr/bin/env bash` — checks `python3 --version`, then runs `python3 run.py` |
| **macOS** | `start_jarvis.command` | Same as Linux `.sh`, but `.command` extension makes it double-clickable in Finder |
| **Shared** | `start_jarvis.sh` | A single POSIX shell script that works on both Linux and macOS |

Make the shell script executable (`chmod +x start_jarvis.sh`).

#### Effort Estimate: **Low** (< 0.5 day)
Just write two files. No logic changes.

---

### 4. `start_jarvis_boot.vbs` (5 lines) — ⚠️ LOW EFFORT

**Status:** VBScript auto-start launcher, generated by `desktop/startup.py`.

Becomes obsolete once `desktop/startup.py` is ported (the new mechanism writes `.plist` or `.desktop` files directly, no intermediate launcher needed). Can remain in the repo for backward compat with Windows — simply ignored on other platforms.

#### Effort Estimate: **Low** (part of startup.py rewrite)

---

## ⚠️ Components Needing Minor Changes

These modules mostly work cross-platform but have small Windows-isms that need updating.

### 1. `backend/tools.py` — `DEFAULT_APPS` dictionary

**Problem:** Hardcoded Windows executable paths:

```python
"chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
"firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
"notepad": "notepad.exe",
"cmd": "cmd.exe",
# ... etc.
```

**What to change:** Branch the app dictionary by platform:

```python
import sys

if sys.platform == "win32":
    DEFAULT_APPS = { ... }  # Current Windows paths
elif sys.platform == "darwin":
    DEFAULT_APPS = {
        "calculator": "open -a Calculator",
        "notepad": "open -a TextEdit",
        "terminal": "open -a Terminal",
        "chrome": "open -a 'Google Chrome'",
        "firefox": "open -a Firefox",
        # ...
    }
else:  # Linux
    DEFAULT_APPS = {
        "calculator": "gnome-calculator",
        "notepad": "gedit",
        "terminal": "gnome-terminal",
        "chrome": "google-chrome",
        "firefox": "firefox",
        # ...
    }
```

**Effort Estimate:** **Low** (< 0.5 day)

---

### 2. `backend/tools.py` — `open_app()` function

**Problem:** Uses `subprocess.Popen(cmd, shell=True)` which:
- Is a security anti-pattern (shell injection risk).
- Works differently on Unix (shell interprets the command) vs Windows (cmd.exe interprets it).
- With platform-branched DEFAULT_APPS, some values will be `"open -a Calculator"` (macOS) which needs shell=True, while others like `"gnome-calculator"` (Linux) can use a list without shell.

**What to change:** Two approaches:
1. **Keep `shell=True`** but sanitize input more strictly. Simple, works, but not ideal.
2. **Refactor** to check if the command contains spaces/special chars → use `shell=True`, otherwise use list form.

**Effort Estimate:** **Low** (< 0.5 day) — this is already documented as potentially fragile.

---

### 3. `backend/tools.py` — `SAFE_COMMANDS` set

**Problem:** Already has both Windows and Unix commands — good! But could be more complete for Unix.

```
SAFE_COMMANDS = {
    "dir", "ls", "echo", "type", "find", "findstr", "where",
    "ipconfig", "ping", "nslookup", "tracert", "netstat",
    "systeminfo", "tasklist", "whoami", "ver", "date", "time",
    "chcp", "cd", "pwd", "help",
}
```

**What to change:** Add more Unix-safe commands:
```python
SAFE_COMMANDS = {
    # Windows
    "dir", "type", "find", "findstr", "where", "ipconfig",
    "systeminfo", "tasklist", "chcp", "ver",
    # Unix
    "ls", "pwd", "cat", "head", "tail", "less", "more",
    "uname", "hostname", "whoami", "uptime", "df", "du",
    "ps", "top", "free", "date", "time", "cal",
    "echo", "which", "env", "printenv",
    # Cross-platform
    "ping", "nslookup", "host", "netstat", "curl", "wget",
    "cd", "help",
}
```

**Effort Estimate:** **Low** (15 minutes)

---

### 4. `backend/config.py` — `_default_apps()`

**Problem:** Returns Windows-specific default apps:
```python
{"name": "Command Prompt", "command": "cmd", "args": ""},
{"name": "Calculator", "command": "calc", "args": ""},
{"name": "File Explorer", "command": "explorer", "args": ""},
# ... etc.
```

**What to change:** Same pattern as `DEFAULT_APPS` — branch by `sys.platform`.

**Effort Estimate:** **Low** (< 0.5 day)

---

### 5. `backend/config.py` — `HERMES_SOURCE`

**Problem:** Default path is Windows-specific:
```python
HERMES_SOURCE = Path(
    os.environ.get(
        "HERMES_SOURCE",
        Path.home() / "AppData" / "Local" / "hermes" / "hermes-agent",
    )
)
```

**Status:** ✅ **Practically a non-issue.** This variable is **never actually read** anywhere in the codebase (the agent.py module doesn't import from Hermes — it makes direct API calls). The file already has a comment documenting the macOS and Linux equivalents. Left as-is, this causes no runtime errors on other platforms. Only needs updating if Hermes integration is re-enabled in the future.

**Effort Estimate:** **Very Low** (can leave as-is, update comment only)

---

## Suggested Migration Path

### Phase 1: Core Server on Linux/macOS (2–3 days)
**Goal:** The web server runs, AI chat works, file/web tools work. OS-level control (volume, screenshots, typing) returns "not available on this platform" errors gracefully.

| Step | Files | Changes |
|------|-------|---------|
| 1.1 | `backend/tools.py` | Branch `DEFAULT_APPS` by `sys.platform`. Expand `SAFE_COMMANDS` set. Update `open_app()` to handle platform-specific commands. |
| 1.2 | `backend/config.py` | Branch `_default_apps()` by platform. Leave `HERMES_SOURCE` as-is (not used). |
| 1.3 | `backend/pc_control.py` | Add `sys.platform` branching. For Linux/macOS: stub out `set_volume`, `mute_audio`, `type_text`, `take_screenshot` with `{"success": False, "error": "Not available on this platform"}` or implement via `pyautogui`/`psutil`. Implement `launch_app` with `xdg-open`/`open`. |
| 1.4 | Project root | Create `start_jarvis.sh`. Add execution instructions for Linux/macOS to README. |

**At the end of Phase 1, the server can be started and the full chat experience works on all three platforms.** The Settings page works, provider configuration works, TTS/STT work, file operations work, and web search works.

### Phase 2: Full OS-Level Control (2–3 days)
**Goal:** All `pc_control.py` functions work on all platforms.

| Step | Files | Changes |
|------|-------|---------|
| 2.1 | `backend/pc_control.py` | Install `pyautogui` and `psutil` as optional dependencies. Implement `take_screenshot()` via `pyautogui.screenshot()`. Implement `get_system_status()` via `psutil`. Implement `type_text()` via `pyautogui.typewrite()`. |
| 2.2 | `backend/pc_control.py` | Implement `set_volume()` with `pactl` (Linux) and `osascript` (macOS). |
| 2.3 | `backend/pc_control.py` | Implement `mute_audio()` with `pactl` (Linux) and `osascript` (macOS). |
| 2.4 | `backend/requirements.txt` | Add `pyautogui` and `psutil` as optional extras (e.g., `pip install jarvis-desktop[full]`). |

### Phase 3: Auto-Start & Polish (1 day)
**Goal:** Jarvis can be configured to auto-start on login on all platforms.

| Step | Files | Changes |
|------|-------|---------|
| 3.1 | `desktop/startup.py` | Add `sys.platform` branching. Implement `register()`/`unregister()`/`is_registered()` for LaunchAgents (macOS) and autostart `.desktop` files (Linux). |
| 3.2 | `start_jarvis_boot.vbs` | Leave as Windows-only artifact. Add note that it's unused on other platforms. |
| 3.3 | `start_jarvis.bat` | Keep for Windows. Document alternative for Unix. |

### Phase 4: Desktop Notifications & System Tray (Optional, 1–2 days)
**Goal:** Native desktop notifications and optionally a system tray icon.

| Step | Changes |
|------|---------|
| 4.1 | Add cross-platform notifications via `plyer` or `notify-py`. |
| 4.2 | Add system tray icon via `pystray` (cross-platform). |

---

## Keeping Backward Compatibility with Windows

The recommended migration approach **preserves full backward compatibility** by design:

1. **No existing Windows code is removed or modified in its code path.** All changes use `if sys.platform == "win32": ... elif sys.platform == "darwin": ... else: ...` branching. The existing Windows implementations (PowerShell, VBScript, `%APPDATA%\...\Startup`) remain untouched.

2. **New files are additive.** `start_jarvis.sh` is added alongside `start_jarvis.bat`. The VBS launcher is kept for Windows users.

3. **Optional dependencies.** `pyautogui` and `psutil` are added as optional extras. The minimal `requirements.txt` install still works identically on Windows — users get the same experience. Only those who want macOS/Linux desktop features need the extras.

4. **The test suite** (if any) should test the core chat and web search on all three platforms, while OS-level control tests are platform-specific.

5. **Recommendation:** After each phase, run `start_jarvis.bat` on a Windows machine to verify nothing regressed.

---

## Summary Table

| Module | Status | Effort | Phase |
|--------|--------|--------|-------|
| `backend/server.py` | ✅ Cross-platform | None | — |
| `backend/agent.py` | ✅ Cross-platform | None | — |
| `backend/tools.py` (file ops, web, dispatch) | ✅ Cross-platform | None | — |
| `backend/tools.py` (DEFAULT_APPS) | ⚠️ Minor change | Low | Phase 1 |
| `backend/tools.py` (open_app) | ⚠️ Minor change | Low | Phase 1 |
| `backend/tools.py` (SAFE_COMMANDS) | ⚠️ Minor change | Low | Phase 1 |
| `backend/config.py` (default apps) | ⚠️ Minor change | Low | Phase 1 |
| `backend/config.py` (HERMES_SOURCE) | ✅ Practically cross-platform | Very Low | — |
| `backend/pc_control.py` | ❌ Windows-only — **largest blocker** | High | Phase 1 & 2 |
| `desktop/startup.py` | ❌ Windows-only | Medium | Phase 3 |
| `start_jarvis.bat` | ❌ Windows-only | Low | Phase 1 |
| `start_jarvis_boot.vbs` | ❌ Windows-only (generated) | Low | Phase 3 |
| `frontend/index.html` | ✅ Cross-platform | None | — |
| `run_server.py` | ✅ Cross-platform | None | — |
| `backend/requirements.txt` | ✅ Cross-platform deps | None | — |

---

## Appendix: Platform Detection Cheat Sheet

```python
import sys, platform

# OS type (most commonly needed)
sys.platform
# → 'win32'    (Windows, even 64-bit)
# → 'darwin'   (macOS)
# → 'linux'    (Linux, all distros)

# More detailed
platform.system()
# → 'Windows', 'Darwin', 'Linux'

platform.release()
# → '10', '23.1.0', '6.5.0-14-generic'
```

### Cross-Platform Command Reference

| Action | Windows | macOS | Linux |
|--------|---------|-------|-------|
| Open file/app | `start <file>` | `open <file>` | `xdg-open <file>` |
| Launch terminal | `cmd.exe` / `powershell.exe` | `Terminal.app` | `gnome-terminal`, `konsole`, `xterm` |
| Set volume | PowerShell `WMPlayer.OCX` | `osascript -e "set volume 50"` | `pactl set-sink-volume @DEFAULT_SINK@ 50%` |
| Mute/unmute | PowerShell SendKeys | `osascript -e "set volume output muted true"` | `pactl set-sink-mute @DEFAULT_SINK@ toggle` |
| Screenshot | PowerShell WinForms | `screencapture <file>` | `import <file>` (ImageMagick) |
| CPU/Memory | `wmic` / PowerShell CIM | `sysctl`, `vm_stat` | `/proc/stat`, `/proc/meminfo` |
| Auto-start dir | `%APPDATA%\...\Startup\` | `~/Library/LaunchAgents/` | `~/.config/autostart/` |
| Auto-start format | `.lnk` shortcut | `.plist` file | `.desktop` file |

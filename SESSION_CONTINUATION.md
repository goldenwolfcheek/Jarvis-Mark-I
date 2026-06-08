# Jarvis Mark 1 — Session Continuation Document
# Generated: June 08, 2026
# Model: big-pickle / Provider: opencode-zen

## ⚡ CRITICAL: Current Server Status
- Server: **RUNNING** at http://127.0.0.1:9119
- Start command: `cd /i/Code\ Shit/OpenCode/Projects/Jarvis\ Mark\ 1 && .venv/Scripts/python.exe run_server.py`
- Kill: `for pid in $(netstat -ano | grep ':9119' | grep LISTEN | awk '{print $NF}'); do taskkill //F //PID $pid; done`
- Default model: deepseek-v4-flash-free (free tier, no API key needed)
- Provider: opencode-zen, base_url: https://opencode.ai/zen/v1

## Project Structure
```
I:\Code Shit\OpenCode\Projects\Jarvis Mark 1\
├── backend/
│   ├── __init__.py
│   ├── server.py      # FastAPI server (15 REST endpoints + WebSocket /api/chat)
│   ├── agent.py       # OpenAI-compatible chat client with tool calling loop
│   ├── tools.py       # 7 tools: create_file, read_file, web_fetch, web_search, open_app, list_apps, execute_command
│   ├── config.py      # Config load/save (JSON, ~/.jarvis/config.json)
│   └── pc_control.py  # PC control: launch apps, volume, typing, screenshots
├── frontend/
│   └── index.html     # FULL single-file app: Three.js dual sphere + chat UI + settings
├── run_server.py      # Entry point
├── run.py             # Alternative entry
├── start_jarvis.bat    # Windows batch launcher
├── desktop/           # (future) PyQt6 desktop app
├── references/
│   └── mark-xl-analysis.md  # Analysis of Mark-XL repo for future features
└── .venv/             # uv-managed venv
```

## Architecture
- **Backend:** FastAPI server with WebSocket for streaming chat
- **Frontend:** Single `index.html` served statically; Three.js renders dual particle sphere
- **Chat flow:** WebSocket → agent.chat() → OpenAI-compatible API call → streaming deltas
- **Tool calling:** 2-phase non-streaming loop; detects both JSON and XML tool calls

## All Completed Features (Mark 1)
1. ✅ Dual particle sphere (fixed outer + pulsing inner + starfield + HUD rings)
2. ✅ 7 tools: create_file, read_file, web_fetch, web_search, open_app, list_apps, execute_command
3. ✅ Auto model detection (tests each model via API, shows only accessible ones)
4. ✅ 9 providers: OpenAI, OpenCode Zen, OpenRouter, Google Gemini, Anthropic, NVIDIA NIM, Ollama, LM Studio, Custom
5. ✅ Provider Keys Manager (edit API keys for any provider in Settings)
6. ✅ Subtitles (toggleable) — shows AI speech above sphere during responses
7. ✅ Chat input visibility (toggleable) — hides chat bubbles, keeps input/input area
8. ✅ TTS with emoji stripping (both frontend and backend strip emojis)
9. ✅ Conversation memory (WebSocket session maintains conversation list)
10. ✅ Model persistence (saves selected model to config + localStorage)
11. ✅ 18 security/code quality fixes (shell injection whitelist, CORS restricted, path traversal fixed, unused code removed)
12. ✅ Connection status badge at bottom ("SYSTEM ONLINE" / "SYSTEM OFFLINE")

## Key Technical Details

### WebSocket Protocol
- Connect: ws://127.0.0.1:9119/api/chat
- Send: `{"type":"message","text":"Hello"}`
- Receive: `{"type":"thinking","text":""}`, `{"type":"delta","text":"Hi"}`, `{"type":"done","text":"Hi there!"}`, `{"type":"error","text":"..."}`

### Tool Calling (XML Support)
- Free models output XML: `<tool_calls><invoke name="web_search"><parameter name="query">...</parameter></invoke></tool_calls>`
- Paid models output JSON: `{"tool_calls":[{"function":{"name":"web_search","arguments":"{..."}}]}`
- Agent handles both formats via non-streaming loop (max 6 turns)
- XML models get tool results injected as user messages (no `role:tool` support)
- Native models use proper `role:tool` + `tool_call_id` format

### Model Selector
- Auto-fetches from provider's /v1/models endpoint
- Validates accessibility: tests each paid model with 1-token API call (max 15s)
- Free models always included (pattern-matched from 11 known free model names)
- Custom model input via "✏️ Custom model..." option

### Provider Keys Manager (in Settings)
- Per-provider API key storage
- Toggle visibility, inline editing
- Keys stored in ~/.jarvis/config.json (plaintext — known limitation)

### Security Improvements (from audit)
- execute_command: blacklist → whitelist (18 safe commands, no shell=True)
- open_app: no raw input fallthrough (returns error for unknown apps)
- CORS: * → ["http://127.0.0.1:9119", "http://localhost:9119"]
- Path traversal: os.path.normpath + os.path.abspath validation
- WhisperModel: singleton (was reloading ~1.4GB per STT request)
- tempfile.mktemp() → NamedTemporaryFile
- 6 unused imports removed

### Free Models Available (OpenCode Zen)
```
claude-haiku-4-5, deepseek-v4-flash, qwen3.6-plus, qwen3.5-plus,
big-pickle, deepseek-v4-flash-free, mimo-v2.5-free, qwen3.6-plus-free,
minimax-m3-free, nemotron-3-ultra-free, nemotron-3-super-free
```

## Current Bugs/Issues
- **Known minor bugs remain** (connection badge occasionally glitchy on rapid reconnect, settings panel sync edge cases) — but functionally complete for Mark 1 release.
- Mark 1 is **concluded** as of June 08, 2026. Work continues in `Jarvis Mark II\`.

## Fixes Applied (June 08, 2026)

### Connection Status Badge
- **Root cause:** JavaScript referenced `document.getElementById('status-text')` but the HTML element's ID was `connection-status`. The `statusText` variable was `null`, so all status updates silently failed.
- **Fix:** Changed the JS reference to `document.getElementById('connection-status')` and added proper CSS class toggling (`.online`/`.offline`) for visual states.
- **States:** "SYSTEM ONLINE" (green), "SYSTEM OFFLINE" (red, on error), "RECONNECTING..." (red, on WebSocket close), "CONNECTION ERROR" (red, on WebSocket error).

### Start on Boot
- **Root cause:** `desktop/startup.py` referenced `desktop/main.py` as the launcher target, but the VBS script had path issues and there were no API endpoints to hook the frontend toggle to the actual registration logic.
- **Fix:**
  1. Rewrote `desktop/startup.py` to point at `run_server.py` instead of the non-existent `desktop/main.py`, with a cleaner VBS launcher and PowerShell shortcut creation.
  2. Added 3 API endpoints in `server.py`: `GET /api/startup/status`, `POST /api/startup/register`, `POST /api/startup/unregister`.
  3. Updated `POST /api/config` to auto-call `register()`/`unregister()` when `start_on_boot` is toggled.
  4. Updated frontend to verify actual startup registration status when loading settings.
- **API keys stored plaintext** in JSON config (known limitation, no OS keychain on Windows)

## Next Phase: Mark 2
Planned features for desktop app version:
1. PyQt6 desktop window (no browser)
2. System tray + minimize to tray
3. Always-on voice wake word
4. Screen awareness (screenshot + analysis)
5. Persistent memory across sessions (using Mark-XL's memory manager pattern)
6. HUD overlay / minimal mode

## Important Notes for Future Sessions
- User name: Josh
- Project uses uv for Python package management (not pip)
- OpenCode Zen free models can NOT use OpenAI function calling — they output XML instead
- TTS uses Edge TTS (free, en-US-GuyNeural voice)
- All API keys stored plaintext in JSON config (known limitation, no OS keychain on Windows)
- Three.js loaded via importmap from CDN (three@0.160.0)
- WebSocket reconnects every 3s on disconnect (no exponential backoff — known limitation)
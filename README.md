# 🛸 J.A.R.V.I.S. Mark 1

```
       ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
       ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
       ██║███████║██████╔╝██║   ██║██║███████╗
  ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
  ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
   ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
           ════════════ Mark 1 ════════════
```

**An AI desktop assistant inspired by Iron Man's J.A.R.V.I.S.**  
Built with FastAPI, Three.js, and an extensible multi-provider agent framework.

---

## ✨ Features

| Category | Feature | Description |
|----------|---------|-------------|
| 💬 **Chat** | Real-time AI conversation | WebSocket-powered chat with streaming responses |
| 🎨 **UI** | 3D Holographic interface | Three.js animated sphere with cyberpunk aesthetic |
| 🧠 **AI** | 9 provider support | OpenAI, OpenCode Zen, OpenRouter, Google Gemini, Anthropic, NVIDIA NIM, Ollama, LM Studio, Custom |
| 🧰 **AI** | Model discovery | Auto-fetch & validate models from any provider |
| 🛠️ **AI** | 7 built-in tools | `create_file`, `read_file`, `web_fetch`, `web_search`, `open_app`, `list_apps`, `execute_command` |
| 🎙️ **Speech** | Speech-to-Text | Local faster-whisper (offline) + file upload support |
| 🔊 **Speech** | Text-to-Speech | Edge TTS with natural voices |
| 🖥️ **PC** | App launcher | Launch registered apps by name (Discord, VS Code, Steam, etc.) |
| 🔊 **PC** | Volume control | Set system volume (0–100%) |
| ⌨️ **PC** | Keyboard simulation | Type text programmatically via PowerShell SendKeys |
| 📸 **PC** | Screenshots | Capture and save screenshots |
| 📊 **PC** | System monitor | Real-time CPU & memory usage |
| ⚙️ **Config** | Provider settings | UI or API-driven model, key & base URL configuration |
| 🔑 **Config** | Per-provider API keys | Securely store keys for multiple providers |
| 🚀 **Config** | Auto-start on boot | Windows startup registration (VBS + shortcut) |
| 📡 **API** | 17+ REST endpoints | Full HTTP API for all features |
| 🔌 **API** | WebSocket chat | Real-time bidirectional communication |

---

## 📸 Screenshot

![Jarvis Mark 1 UI](https://via.placeholder.com/800x500/0a0a0f/00d4ff?text=Jarvis+Mark+1+UI)

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Windows 10/11** (PC control features are Windows-only; server runs cross-platform)
- ~1.5 GB free disk space for the STT model (optional, for voice input)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/jarvis-mark-1.git
cd jarvis-mark-1

# 2. Create a virtual environment
python -m venv .venv
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate    # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
python run_server.py
```

The server starts on **http://127.0.0.1:9119** — open it in your browser.

### Windows One-Click Launch

Double-click **`start_jarvis_boot.vbs`** to launch the server silently (no console window).

---

## ⚙️ Configuration

Jarvis stores its configuration at **`~/.jarvis/config.json`**.  
You can configure everything through the UI's Settings panel or via the REST API.

### Providers

| Provider | ID | Default Base URL |
|----------|----|-----------------|
| OpenAI | `openai` | `https://api.openai.com/v1` |
| OpenCode Zen | `opencode-zen` | `https://opencode.ai/zen/v1` |
| OpenRouter | `openrouter` | `https://openrouter.ai/api/v1` |
| Google Gemini | `google` | `https://generativelanguage.googleapis.com/v1beta/openai` |
| Anthropic | `anthropic` | `https://api.anthropic.com/v1` |
| NVIDIA NIM | `nvidia` | `https://integrate.api.nvidia.com/v1` |
| Ollama (Local) | `ollama` | `http://localhost:11434/v1` |
| LM Studio | `lm-studio` | `http://localhost:1234/v1` |
| Custom | `custom` | *(user-defined)* |

### API Keys

> ⚠️ **Security Warning:** API keys are stored in plaintext in `~/.jarvis/config.json`.  
> Protect this file — do not commit it to version control. The project's `.gitignore` excludes `~/.jarvis/`.

Set a key via the UI Settings panel, or the API:

```bash
curl -X POST http://127.0.0.1:9119/api/provider/set \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","api_key":"sk-...","model":"gpt-4o"}'
```

---

## 🌐 API Overview

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve frontend UI |
| `GET` | `/api/status` | Server status & version |
| `GET` | `/api/config` | Get configuration |
| `POST` | `/api/config` | Update configuration |
| `GET` | `/api/providers` | List known providers |
| `GET` | `/api/provider` | Current provider (key masked) |
| `POST` | `/api/provider/set` | Set active provider/model/key |
| `GET` | `/api/provider/keys` | Per-provider key status |
| `POST` | `/api/provider/keys` | Save per-provider keys |
| `POST` | `/api/provider/test` | Test provider connection |
| `POST` | `/api/provider/models` | Fetch available models |
| `GET` | `/api/apps` | List registered apps |
| `POST` | `/api/apps` | Register an app |
| `DELETE` | `/api/apps` | Remove a registered app |
| `POST` | `/api/launch` | Launch app by command |
| `POST` | `/api/launch-by-name` | Launch app by registered name |
| `GET` | `/api/system/status` | CPU & memory usage |
| `POST` | `/api/volume` | Set volume (0–100) |
| `POST` | `/api/type` | Type text via keyboard |
| `POST` | `/api/screenshot` | Take a screenshot |
| `POST` | `/api/tts` | Text-to-Speech |
| `POST` | `/api/stt` | Speech-to-Text (by path) |
| `POST` | `/api/stt/upload` | Speech-to-Text (file upload) |
| `GET` | `/api/audio/file` | Serve generated audio |
| `GET` | `/api/startup/status` | Auto-start status |
| `POST` | `/api/startup/register` | Register auto-start |
| `POST` | `/api/startup/unregister` | Remove auto-start |

### WebSocket Protocol

Connect to **`ws://127.0.0.1:9119/api/chat`** for real-time conversation.

**Client → Server:**
```json
{"type": "message", "text": "Hello Jarvis"}
```

**Server → Client (streaming):**
```json
{"type": "thinking", "text": ""}        // Thinking indicator
{"type": "delta", "text": "Hi there"}  // Streaming chunk
{"type": "done", "text": "Hi there! How can I help you today, sir?"}  // Final
{"type": "error", "text": "Error: ..."}  // Error
```

---

## 🛠️ AI Tools

Jarvis can use these tools via OpenAI-compatible function calling (or XML-style tool calls for models that don't support native function calling):

| Tool | Description |
|------|-------------|
| `create_file(path, content)` | Create or overwrite a file |
| `read_file(path)` | Read a file's contents (max 50K chars) |
| `web_fetch(url)` | Fetch a web page as plain text |
| `web_search(query)` | Search the web via DuckDuckGo |
| `open_app(app)` | Launch an application by name |
| `list_apps()` | List all registered applications |
| `execute_command(command)` | Run a whitelisted shell command |

Shell commands are restricted to a **safety whitelist** (`ls`, `dir`, `echo`, `ping`, `ipconfig`, etc.) — arbitrary command execution is blocked.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Browser (Frontend)                  │
│  ┌─────────────────────────────────────────────────┐ │
│  │   Three.js 3D UI (index.html)                   │ │
│  │   - Animated holographic sphere                 │ │
│  │   - Chat interface + settings panel             │ │
│  │   - Connection status badge                     │ │
│  └──────────────┬──────────────────────────────────┘ │
└─────────────────┼────────────────────────────────────┘
                  │ WebSocket (ws://) / HTTP
                  ▼
┌──────────────────────────────────────────────────────┐
│              FastAPI Backend (port 9119)              │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │ server.py │→│ agent.py │→│ OpenAI-compatible    │  │
│  │ (routing) │ │ (chat)   │ │  API (any provider)  │  │
│  └─────┬─────┘ └────┬─────┘ └──────────────────────┘  │
│        │            │                                  │
│        ▼            ▼                                  │
│  ┌──────────┐ ┌──────────┐                           │
│  │ tools.py │ │config.py │                           │
│  │ (7 tools)│ │(settings)│                           │
│  └────┬─────┘ └──────────┘                           │
│       │                                              │
│       ▼                                              │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐   │
│  │pc_control│ │ startup  │ │ TTS / STT          │   │
│  │(Windows) │ │ (auto-   │ │ edge-tts, whisper  │   │
│  │          │ │  start)  │ │                    │   │
│  └──────────┘ └──────────┘ └────────────────────┘   │
└──────────────────────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────────┐
│                    OS Layer                           │
│  File system │ Shell │ Apps │ Audio │ Display        │
└──────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
jarvis-mark-1/
├── backend/
│   ├── server.py          # FastAPI server (17+ endpoints + WebSocket)
│   ├── agent.py           # OpenAI-compatible API client
│   ├── tools.py           # Tool definitions & execution engine
│   ├── config.py          # Config load/save (JSON)
│   └── pc_control.py      # Windows PC control (PowerShell)
├── frontend/
│   └── index.html         # Single-page Three.js UI (~1970 lines)
├── desktop/
│   └── startup.py         # Windows auto-start registration
├── run_server.py          # Entry point — starts uvicorn
├── start_jarvis_boot.vbs  # Silent VBS launcher (auto-start)
├── requirements.txt       # Python dependencies
├── .gitignore
└── README.md
```

---

## 🔄 Cross-Platform Notes

| Component | Windows | macOS | Linux |
|-----------|---------|-------|-------|
| FastAPI server | ✓ | ✓ | ✓ |
| Frontend (Three.js) | ✓ | ✓ | ✓ |
| AI agent (agent.py) | ✓ | ✓ | ✓ |
| Tools (file ops, web) | ✓ | ✓ | ✓ |
| TTS (edge-tts) | ✓ | ✓ | ✓ |
| STT (faster-whisper) | ✓ | ✓ | ✓ |
| PC control (launch, volume, typing, screenshots) | ✓ | ✗ | ✗ |
| Auto-start on boot | ✓ | ✗ | ✗ |

Platform-specific logic is isolated to `backend/pc_control.py` and `desktop/startup.py`. To port PC control to macOS/Linux, replace PowerShell calls with platform equivalents (e.g., `osascript` on macOS, `pactl`/`xdg-open` on Linux).

---

## 🤝 Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes and test them.
4. Commit with clear messages.
5. Push and open a Pull Request.

### Development

- The server auto-reloads changes with `uvicorn.run()` — restart manually after edits.
- Test the API with `test_api.py` or any HTTP client.
- The frontend is a single HTML file — no build step required.

---

## 📄 License

**MIT License** — see `LICENSE` for details.

---

<p align="center">
  <sub>Built with ❤️ using FastAPI, Three.js, and Edge TTS</sub><br>
  <sub>J.A.R.V.I.S. is a fictional AI from Marvel's Iron Man — this is a fan project.</sub>
</p>

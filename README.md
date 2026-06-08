# J.A.R.V.I.S. Mark I

**Just A Rather Very Intelligent System** — An AI-powered desktop assistant inspired by Iron Man's JARVIS.

Built with a FastAPI backend and a Three.js 3D holographic web interface. Supports multiple AI providers, tools, and PC control.

> ⚠️ **Early Development Phase** — This is Mark 1 of a planned 20+ version series. Bugs and incomplete features are expected. See [Known Bugs](#-known-bugs) below.

> ⚠️ **Hobby Project/Concept Idea** — This is a project made by someone who doesn't know how to code but wanted to have something close to a real life Jarvis. I can understand the hate for AI but let's be real, the idea of Jarvis is cool (just without the whole Ultron thing). The goal if this project is to make something similar to Jarvis utilizing projects like [Hermes](https://hermes-agent.nousresearch.com/) and [Odysseus](https://github.com/pewdiepie-archdaemon/odysseus) to build the ultimate AI assistant.

---

## ⚡ Quick Start

### Requirements
- **Python 3.8+** ([python.org](https://python.org))
- Approximately 4GB of free disk space (for dependencies and optional speech models)

### Windows (One-Click)
1. Download or clone this repository
2. Double-click **`start_jarvis.bat`**
3. Wait for dependencies to install (first run only)
4. Your browser should open to `http://127.0.0.1:9119`

### Manual Setup (All Platforms)
```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/Jarvis-Mark-1.git
cd Jarvis-Mark-1

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Start Jarvis
python run_server.py
```

### Verify It's Running
Open your browser to **http://127.0.0.1:9119**

You should see:
- Animated UI with spheres (holographic interface)
- Connection status badge at bottom: **"SYSTEM ONLINE"**
- A chat input area, with a model selector in the bottom left

---

## 🔌 Connecting an AI Provider

Jarvis supports **8+ providers**. You need at least one configured to chat.

### Free Option (No API Key Required)
The default provider is **OpenCode Zen** — it offers free models with no API key needed:
1. Open the Jarvis UI at `http://127.0.0.1:9119`
2. Click the **gear icon** (Settings) in the top-right corner
3. Select **"OpenCode Zen"** from the Provider dropdown
4. Leave the API key field empty
5. Click **"Save Provider"**
6. Click **Save**, then select a free model from the model selector (e.g., `big-pickle`)

### Paid Providers (API Key Required)
1. Open Settings → Provider dropdown
2. Select your provider (OpenAI, OpenRouter, Anthropic, Google Gemini, etc.)
3. Enter your API key in the field
4. Click **"Test Connection"** and then **"Save Provider"** to see available models
5. Select a model, then chat away!

| Provider | Base URL | API Key Needed |
|----------|----------|----------------|
| OpenCode Zen | `https://opencode.ai/zen/v1` | No (free models) |
| OpenAI | `https://api.openai.com/v1` | Yes |
| OpenRouter | `https://openrouter.ai/api/v1` | Yes |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | Yes |
| Anthropic | `https://api.anthropic.com/v1` | Yes |
| NVIDIA NIM | `https://integrate.api.nvidia.com/v1` | Yes |
| Ollama (Local) | `http://localhost:11434/v1` | No |
| LM Studio | `http://localhost:1234/v1` | No |
| Custom | Your own URL | Varies |

> 🔐 **API keys are stored in plaintext** at `~/.jarvis/config.json`. This is a known limitation — no OS keychain integration yet.

---

## 🧰 What Jarvis Can Do (Tools)

Once connected, Jarvis has these capabilities:

| Tool | What It Does |
|------|-------------|
| `create_file` | Create or overwrite files anywhere on your computer |
| `read_file` | Read the contents of any file |
| `web_fetch` | Fetch and extract text from any webpage |
| `web_search` | Search the web using DuckDuckGo (free, no API key) |
| `open_app` | Launch applications (calculator, notepad, Chrome, Discord, etc.) |
| `list_apps` | Show all registered applications |
| `execute_command` | Run safe shell commands (read-only whitelist) |

Example conversation:
> **You:** "Search the web for today's top tech news"  
> **Jarvis:** Searches the web and returns results  
>
> **You:** "Create a file called notes.txt on my desktop"  
> **Jarvis:** Creates the file with your specified content

---

## 🌐 API Overview

Jarvis provides a WebSocket API for real-time chat and REST endpoints for configuration.

### WebSocket Chat (`ws://127.0.0.1:9119/api/chat`)
```
→ {"type": "message", "text": "Hello"}
← {"type": "thinking", "text": ""}
← {"type": "delta", "text": "Hi "}
← {"type": "delta", "text": "there!"}
← {"type": "done", "text": "Hi there!"}
```

### Key REST Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/status` | Server status |
| GET | `/api/config` | Get current config |
| POST | `/api/config` | Update config |
| GET | `/api/providers` | List providers |
| POST | `/api/provider/set` | Set active provider |
| POST | `/api/provider/test` | Test provider connection |
| POST | `/api/provider/models` | Fetch available models |
| POST | `/api/tts` | Text-to-speech |
| POST | `/api/stt` | Speech-to-text |
| GET | `/api/startup/status` | Check auto-start status |

Full documentation available in the source code.

---

## 🐛 Known Bugs (Mark I)

These issues are known and will be addressed in future versions:

| Bug | Status |
|-----|--------|
| Models sometimes don't appear even if a provider is saved and selected | 🗓️ Mark II |
| API errors can appear as responses even with valid API keys | 🗓️ Mark II |
| "Show Subtitle" toggle in settings doesn't work properly | 🗓️ Mark II |
| "Show Chat Input" toggle in settings doesn't work properly | 🗓️ Mark II |
| "Registered Apps" settings page is buggy or non-functional | 🗓️ Mark II |
| Image input untested (no compatible models available for testing) | ❓ Unknown |
| Voice input (speech-to-text) does not work at all | ❌ Broken |
| Local LLMs (Ollama, LM Studio) untested — connections may be buggy | ⚠️ Unverified |
| Server startup can fail with "Python not found" error despite Python being installed | 🗓️ Mark II |

---

## 🤖 AI Disclosure

**This project was entirely built using AI tools** — specifically through conversations with the Hermes Agent (by Nous Research) running various models via OpenCode Zen's free tier.

The author (Josh) provided design direction, bug reports, and feature requests. The actual code, documentation, and architecture were generated by AI agents through iterative prompting.

This is not a commercial product — it's a learning project and proof of concept. All sources will be linked, and all credit will be given where is it due.

---

## 📁 Project Structure

```
Jarvis Mark 1/
├── backend/
│   ├── server.py        # FastAPI server (27 API endpoints + WebSocket)
│   ├── agent.py         # OpenAI-compatible chat client
│   ├── tools.py         # Tool definitions and execution
│   ├── config.py        # Configuration management
│   └── pc_control.py    # Windows PC control (PowerShell)
├── frontend/
│   └── index.html       # Three.js 3D holographic UI
├── desktop/
│   ├── main.py          # Desktop window wrapper (pywebview)
│   └── startup.py       # Windows auto-start registration
├── run_server.py         # Server entry point
├── run.py                # Alternative launcher
├── start_jarvis.bat      # Windows one-click launcher
├── install_deps.py       # Dependency installer
├── references/
│   └── mark-xl-analysis.md
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 📃 Credits

Logic / Backend - [Hermes by Nous Research](https://hermes-agent.nousresearch.com/)
UI Reference - [MARK XL — Local AI Assistant by FaithMakes](https://github.com/FatihMakes/Mark-XL)

---

## 📜 License

MIT License — free to use, modify, and distribute.

---

## 🗺️ Roadmap

- **Mark I** — Current release: Web-based UI, multi-provider support, basic tools, TTS
- **Mark II** — Desktop app, system tray, persistent memory, skills
- **Mark III** — Screen awareness, always-on voice wake word, advanced automation, plugin system
- **Mark IV** — And even more to come .....

This project aims for **20+ versions** until the feature set feels complete or the authors' free API usage credits no longer last long enough to continue development.

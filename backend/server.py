"""Jarvis Mark 1 — FastAPI Server

Serves the Jarvis web UI, handles WebSocket chat, TTS, STT, and PC control.
"""

# ---- Cross-Platform Notes ---------------------------------------------------
# This server uses FastAPI + uvicorn, both fully cross-platform
# (Windows, macOS, Linux).  Platform-specific logic is isolated to:
#
#   backend/pc_control.py   — All functions use PowerShell (Windows-only).
#   backend/tools.py        — DEFAULT_APPS has Windows-only paths;
#                             SAFE_COMMANDS has both Windows & Unix commands
#                             for dual-platform shell support.
#
# The frontend is served as static files — no platform dependency.
# TTS (edge-tts) and STT (faster-whisper) run on all three platforms.
# -----------------------------------------------------------------------------

import asyncio
import json
import logging
import os
import tempfile
import time
import hashlib
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

logger = logging.getLogger("jarvis.server")

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(title="Jarvis Mark 1", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:9119", "http://localhost:9119"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------

_agent_lock = asyncio.Lock()


@app.on_event("startup")
async def startup():
    """Initialize the Jarvis environment."""
    from backend.config import JARVIS_HOME

    (JARVIS_HOME / "screenshots").mkdir(parents=True, exist_ok=True)
    (JARVIS_HOME / "audio").mkdir(parents=True, exist_ok=True)
    logger.info(f"Jarvis Mark 1 starting — data dir: {JARVIS_HOME}")


# ---------------------------------------------------------------------------
# Static file serving (frontend)
# ---------------------------------------------------------------------------

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def serve_index():
    """Serve the main Jarvis UI page."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"error": "Frontend not built yet"}, status_code=503)


# ---------------------------------------------------------------------------
# API: Status
# ---------------------------------------------------------------------------


@app.get("/api/status")
async def api_status():
    """Return server and system status."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "name": "Jarvis Mark 1",
    }


# ---------------------------------------------------------------------------
# API: Configuration
# ---------------------------------------------------------------------------


@app.get("/api/config")
async def get_config():
    """Get current Jarvis configuration."""
    from backend.config import load_config

    return load_config()


@app.post("/api/config")
async def update_config(data: dict):
    """Update Jarvis configuration."""
    from backend.config import load_config, save_config

    cfg = load_config()
    cfg.update(data)
    save_config(cfg)

    # If start_on_boot was toggled, apply immediately
    if "start_on_boot" in data:
        from desktop.startup import register as _register, unregister as _unregister

        if data["start_on_boot"]:
            _register()
        else:
            _unregister()

    # Reset agent if model/provider changed
    from backend.agent import reset_agent

    reset_agent()
    return {"success": True}


# ---------------------------------------------------------------------------
# API: Provider Management (like Hermes' provider selector)
# ---------------------------------------------------------------------------

KNOWN_PROVIDERS = [
    {"id": "openai",         "name": "OpenAI",         "base_url": "https://api.openai.com/v1"},
    {"id": "opencode-zen",   "name": "OpenCode Zen",   "base_url": "https://opencode.ai/zen/v1"},
    {"id": "openrouter",     "name": "OpenRouter",     "base_url": "https://openrouter.ai/api/v1"},
    {"id": "google",         "name": "Google Gemini",  "base_url": "https://generativelanguage.googleapis.com/v1beta/openai"},
    {"id": "anthropic",      "name": "Anthropic",      "base_url": "https://api.anthropic.com/v1"},
    {"id": "nvidia",         "name": "NVIDIA NIM",     "base_url": "https://integrate.api.nvidia.com/v1"},
    {"id": "ollama",         "name": "Ollama (Local)", "base_url": "http://localhost:11434/v1"},
    {"id": "lm-studio",      "name": "LM Studio",      "base_url": "http://localhost:1234/v1"},
    {"id": "custom",         "name": "Custom",         "base_url": ""},
]


@app.get("/api/providers")
async def list_providers():
    """Return list of known provider presets."""
    return {"providers": KNOWN_PROVIDERS}


@app.get("/api/provider")
async def get_provider():
    """Get current provider configuration (API key masked)."""
    from backend.config import load_config

    cfg = load_config()
    provider_id = cfg.get("provider", "")
    # Fall back to per-provider key if main api_key is empty
    api_key = cfg.get("api_key", "")
    if not api_key and provider_id:
        stored_keys = cfg.get("api_keys", {})
        api_key = stored_keys.get(provider_id, "")
    model = cfg.get("model", "")
    base_url = cfg.get("base_url", "")

    # Mask the API key for security
    masked_key = ""
    if api_key and len(api_key) > 8:
        masked_key = api_key[:6] + "*" * (len(api_key) - 8) + api_key[-2:]
    elif api_key:
        masked_key = "*" * len(api_key)

    return {
        "provider": provider_id,
        "model": model,
        "base_url": base_url,
        "api_key_masked": masked_key,
        "has_key": bool(api_key),
    }


@app.post("/api/provider/set")
async def set_provider(data: dict):
    """Set the active provider, model, API key, and base URL.

    Body: {
        "provider": "openai",
        "api_key": "sk-...",
        "model": "gpt-4o",
        "base_url": "https://api.openai.com/v1"   # optional, uses default if omitted
    }
    """
    provider_id = data.get("provider", "").strip()
    if not provider_id:
        # If no provider given, we can still update other fields (model, api_key)
        pass

    from backend.config import load_config, save_config

    cfg = load_config()

    if provider_id:
        cfg["provider"] = provider_id

    # Update API key if provided
    if "api_key" in data and data["api_key"]:
        cfg["api_key"] = data["api_key"].strip()
        # Also store per-provider
        if "api_keys" not in cfg:
            cfg["api_keys"] = {}
        cfg["api_keys"][provider_id] = data["api_key"].strip()

    # Update model if provided
    if "model" in data and data["model"]:
        cfg["model"] = data["model"].strip()

    # Update base_url if provided, or use default for known provider
    if "base_url" in data and data["base_url"]:
        cfg["base_url"] = data["base_url"].strip()
    elif provider_id and provider_id != "custom":
        for p in KNOWN_PROVIDERS:
            if p["id"] == provider_id and p["base_url"]:
                cfg["base_url"] = p["base_url"]
                break

    save_config(cfg)

    # Reset agent so it picks up new config
    from backend.agent import reset_agent
    reset_agent()

    logger.info(f"Provider set to {provider_id} with model {cfg.get('model', '?')}")
    return {"success": True, "provider": provider_id, "model": cfg.get("model", "")}


@app.get("/api/provider/keys")
async def get_provider_keys():
    """Get all providers and whether each has an API key stored."""
    from backend.config import load_config
    
    cfg = load_config()
    stored_keys = cfg.get("api_keys", {})
    
    providers = []
    for p in KNOWN_PROVIDERS:
        pid = p["id"]
        providers.append({
            "id": pid,
            "name": p["name"],
            "has_key": bool(stored_keys.get(pid)),
            "is_current": cfg.get("provider") == pid,
        })
    
    return {"success": True, "providers": providers}


@app.post("/api/provider/keys")
async def save_provider_keys(data: dict):
    """Save API keys for specific providers.
    
    Body: { "openai": "sk-...", "opencode-zen": "sk-...", ... }
    """
    from backend.config import load_config, save_config
    
    cfg = load_config()
    if "api_keys" not in cfg:
        cfg["api_keys"] = {}
    
    updated = 0
    for provider_id, api_key in data.items():
        if not provider_id or not isinstance(provider_id, str):
            continue
        if api_key and isinstance(api_key, str):
            cfg["api_keys"][provider_id] = api_key.strip()
            updated += 1
    
    save_config(cfg)
    return {"success": True, "updated": updated}


@app.post("/api/provider/test")
async def test_provider(data: dict = None):
    """Test the current (or provided) provider connection.

    Sends a simple 'Hello' and checks if we get a response.
    Does NOT permanently change the config — any provided values
    are temporary for this test only.
    """
    from backend.agent import chat as agent_chat
    from backend.config import load_config, save_config

    cfg = load_config()

    # Temporarily override config with test values (if provided)
    if data:
        if data.get("api_key"):
            cfg["api_key"] = data["api_key"].strip()
        if data.get("model"):
            cfg["model"] = data["model"].strip()
        if data.get("provider"):
            cfg["provider"] = data["provider"].strip()
        if data.get("base_url"):
            cfg["base_url"] = data["base_url"].strip()
        elif data.get("provider"):
            for p in KNOWN_PROVIDERS:
                if p["id"] == data["provider"] and p["base_url"]:
                    cfg["base_url"] = p["base_url"]
                    break

    try:
        result = agent_chat("Reply with only the word: OK")
        if result.startswith("Error:"):
            return {"success": False, "message": result[7:]}
        success = len(result) > 0
        return {
            "success": success,
            "message": result[:200] if result else "Empty response (model may be thinking-only)",
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/provider/models")
async def fetch_provider_models(data: dict = None):
    """Fetch available models from a provider, validating access.
    
    Body: { "base_url": "...", "api_key": "..." }
    
    When no API key is provided, returns only models known to be freely
    accessible. When an API key IS provided, tests each model with a
    lightweight API call and returns only the ones that respond successfully.
    """
    from backend.agent import fetch_models as fetch_agent_models
    from backend.config import load_config

    cfg = load_config()
    base_url = (data.get("base_url") if data and data.get("base_url") else cfg.get("base_url", ""))
    api_key = (data.get("api_key") if data and data.get("api_key") else "")
    
    if not base_url:
        return {"success": False, "models": [], "message": "No base_url configured"}
    
    # Fall back to per-provider stored key if none provided
    if not api_key:
        stored_keys = cfg.get("api_keys", {})
        for p in KNOWN_PROVIDERS:
            if p["base_url"] and p["base_url"] in base_url:
                api_key = stored_keys.get(p["id"], "")
                break
    
    # Fetch ALL models from the provider
    models = fetch_agent_models(base_url, api_key)
    
    # Known free model name patterns
    FREE_PATTERNS = ["free", "flash-free", "deepseek", "gpt-4o-mini", "gpt-3.5",
                     "claude-haiku", "gemini-pro", "llama", "mistral", "phi",
                     "mixtral", "qwen", "command-r", "big-pickle", "pig"]
    
    if not api_key:
        # No key → return only free/public models
        filtered = [m for m in models if any(p in m.lower() for p in FREE_PATTERNS)]
        if filtered:
            return {"success": True, "models": filtered}
        return {"success": True, "models": models}
    
    # Has API key → validate which models actually work
    # Free models are always included (no need to test)
    free_models = [m for m in models if any(p in m.lower() for p in FREE_PATTERNS)]
    paid_candidates = [m for m in models if m not in free_models]
    
    if not paid_candidates:
        return {"success": True, "models": free_models}
    
    # Test paid models in parallel batches
    import asyncio, aiohttp
    from asyncio import Semaphore
    from datetime import datetime, timedelta
    
    # Cache validation results for 5 minutes
    cache_key = f"model_validation_{hash(base_url)}_{hash(api_key)}"
    _validation_cache = getattr(app.state, "model_cache", {})
    if cache_key in _validation_cache:
        cached = _validation_cache[cache_key]
        if datetime.now() - cached["time"] < timedelta(minutes=5):
            return {"success": True, "models": free_models + cached["validated"]}
    
    async def test_model(model: str) -> bool:
        """Quick validation: send a 1-token request to see if the model responds."""
        try:
            timeout = aiohttp.ClientTimeout(total=6)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "JarvisMark1/1.0",
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 1,
                    "stream": False,
                }
                async with session.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as resp:
                    if resp.status == 200:
                        body = await resp.json()
                        return bool(body.get("choices") and len(body["choices"]) > 0)
                    return False
        except Exception:
            return False
    
    # Test in batches of 5 concurrent
    sem = Semaphore(5)
    
    async def bounded_test(model: str) -> tuple[str, bool]:
        async with sem:
            return model, await test_model(model)
    
    # Run all tests, but cap total validation time at 15 seconds
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*[bounded_test(m) for m in paid_candidates]),
            timeout=15.0,
        )
    except asyncio.TimeoutError:
        # Return whatever we have after 15 seconds
        results = []
    
    validated_paid = [m for m, ok in results if ok]
    
    # Cache the result
    if not hasattr(app.state, "model_cache"):
        app.state.model_cache = {}
    app.state.model_cache[cache_key] = {
        "time": datetime.now(),
        "validated": validated_paid,
    }
    
    return {"success": True, "models": free_models + validated_paid}


# ---------------------------------------------------------------------------
# API: App Registry
# ---------------------------------------------------------------------------


@app.get("/api/apps")
async def list_apps():
    """List all registered apps."""
    from backend.config import load_registered_apps

    return {"apps": load_registered_apps()}


@app.post("/api/apps")
async def add_app(data: dict):
    """Register a new app."""
    name = data.get("name", "").strip()
    command = data.get("command", "").strip()
    args = data.get("args", "").strip()

    if not name or not command:
        raise HTTPException(status_code=400, detail="name and command are required")

    from backend.config import load_registered_apps, save_registered_apps

    apps = load_registered_apps()
    apps.append({"name": name, "command": command, "args": args})
    save_registered_apps(apps)
    return {"success": True, "apps": apps}


@app.delete("/api/apps")
async def remove_app(data: dict):
    """Remove a registered app by name."""
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    from backend.config import load_registered_apps, save_registered_apps

    apps = load_registered_apps()
    apps = [a for a in apps if a["name"] != name]
    save_registered_apps(apps)
    return {"success": True, "apps": apps}


# ---------------------------------------------------------------------------
# API: PC Control
# ---------------------------------------------------------------------------


@app.post("/api/launch")
async def api_launch_app(data: dict):
    """Launch a registered app."""
    from backend.pc_control import launch_app

    result = await launch_app(data.get("command", ""), data.get("args", ""))
    return result


@app.post("/api/launch-by-name")
async def api_launch_by_name(data: dict):
    """Launch an app by its registered name."""
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    from backend.config import load_registered_apps

    apps = load_registered_apps()
    for app_def in apps:
        if app_def["name"].lower() == name.lower():
            from backend.pc_control import launch_app

            return await launch_app(app_def["command"], app_def.get("args", ""))

    raise HTTPException(status_code=404, detail=f"App '{name}' not found in registry")


@app.get("/api/system/status")
async def api_system_status():
    """Get system status (CPU, memory)."""
    from backend.pc_control import get_system_status

    return await get_system_status()


@app.post("/api/volume")
async def api_set_volume(data: dict):
    """Set system volume (0-100)."""
    from backend.pc_control import set_volume

    return await set_volume(data.get("level", 80))


@app.post("/api/type")
async def api_type_text(data: dict):
    """Type text via keyboard simulation."""
    from backend.pc_control import type_text

    return await type_text(data.get("text", ""))


@app.post("/api/screenshot")
async def api_screenshot():
    """Take a screenshot."""
    from backend.pc_control import take_screenshot

    return await take_screenshot()


# ---------------------------------------------------------------------------
# API: Text-to-Speech
# ---------------------------------------------------------------------------


@app.post("/api/tts")
async def api_tts(data: dict):
    """Convert text to speech audio file.

    Returns the path to the generated audio file.
    """
    text = data.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    # Strip emojis and pictographic symbols from TTS
    import re as _re
    text = _re.sub(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
        r'\U0001F1E0-\U0001F1FF\U00002600-\U000026FF\U00002700-\U000027BF'
        r'\U0000FE00-\U0000FE0F\U0000200D\U00002934\U00002935'
        r'\U000025AA\U000025AB\U000025FB-\U000025FE'
        r'\U00002B05\U00002B06\U00002B07\U00002B1B\U00002B1C'
        r'\U00002B50\U00002B55\U00003030\U0000303D\U00003297\U00003299]',
        '', text
    ).strip()
    if not text:
        return {"success": True, "path": ""}

    from backend.config import load_config, JARVIS_HOME

    cfg = load_config()
    provider = cfg.get("tts_provider", "edge")

    audio_dir = JARVIS_HOME / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    import time

    hash_id = hashlib.md5(text.encode()).hexdigest()[:10]
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = str(audio_dir / f"jarvis_{timestamp}_{hash_id}.mp3")

    try:
        if provider == "edge":
            # Use Edge TTS (free, offline-capable)
            import edge_tts

            voice = data.get("voice", "en-US-GuyNeural")
            await edge_tts.Communicate(text, voice).save(output_path)
        else:
            return {
                "success": False,
                "error": f"TTS provider '{provider}' not available",
            }

        return {"success": True, "path": output_path}
    except Exception as e:
        logger.exception("TTS error")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# API: Start on Boot
# ---------------------------------------------------------------------------


@app.get("/api/startup/status")
async def get_startup_status():
    """Check if Jarvis is registered for auto-start on boot."""
    from desktop.startup import is_registered

    return {
        "success": True,
        "registered": is_registered(),
    }


@app.post("/api/startup/register")
async def api_startup_register():
    """Register Jarvis to auto-start on boot."""
    from desktop.startup import register as _register

    return _register()


@app.post("/api/startup/unregister")
async def api_startup_unregister():
    """Remove Jarvis from auto-start on boot."""
    from desktop.startup import unregister as _unregister

    return _unregister()


# ---------------------------------------------------------------------------
# API: STT Health Check
# ---------------------------------------------------------------------------

# Lazy-loaded singleton for faster-whisper (avoids re-loading ~1.4GB model every request)
_whisper_model = None

def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model


@app.post("/api/stt")
async def api_stt(data: dict):
    """Transcribe audio file to text."""
    audio_path = data.get("path", "").strip()
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=400, detail="Valid audio path is required")

    try:
        from backend.config import load_config

        cfg = load_config()
        provider = cfg.get("stt_provider", "local")

        if provider == "local":
            # Use cached whisper model singleton (avoids re-loading 1.4GB model)
            model = _get_whisper_model()
            segments, _ = model.transcribe(audio_path)
            text = " ".join(seg.text for seg in segments)
            return {"success": True, "text": text}
        else:
            return {"success": False, "error": f"STT provider '{provider}' not available"}
    except Exception as e:
        logger.exception("STT error")
        return {"success": False, "error": str(e)}


@app.post("/api/stt/upload")
async def api_stt_upload(file: UploadFile = File(...)):
    """Upload and transcribe an audio file."""
    if not file:
        raise HTTPException(status_code=400, detail="audio file is required")

    tmp = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
    tmp_path = tmp.name
    try:
        contents = await file.read()
        tmp.write(contents)
        tmp.close()

        # Try local whisper
        try:
            model = _get_whisper_model()
            segments, _ = model.transcribe(tmp_path)
            text = " ".join(seg.text for seg in segments)
            return {"success": True, "text": text}
        except ImportError:
            # Fallback: just acknowledge
            return {"success": False, "error": "STT not available (install faster-whisper)"}
    except Exception as e:
        logger.exception("STT upload error")
        return {"success": False, "error": str(e)}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ---------------------------------------------------------------------------
# API: Audio file serving
# ---------------------------------------------------------------------------


@app.get("/api/audio/file")
async def serve_audio_file(path: str = ""):
    """Serve a generated audio file for TTS playback."""
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Security: only serve files from the Jarvis audio directory
    from backend.config import JARVIS_HOME

    audio_dir = os.path.normpath(str(JARVIS_HOME / "audio"))
    resolved = os.path.normpath(os.path.abspath(path))
    if not resolved.startswith(audio_dir):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(resolved, media_type="audio/mpeg")


# ---------------------------------------------------------------------------
# WebSocket: Chat
# ---------------------------------------------------------------------------


@app.websocket("/api/chat")
async def chat_websocket(ws: WebSocket):
    """WebSocket endpoint for real-time chat with Jarvis.

    Protocol:
      Client -> Server: {"type": "message", "text": "Hello"}
      Server -> Client: {"type": "delta", "text": "Hi "}       (streaming)
      Server -> Client: {"type": "delta", "text": "there!"}     (streaming)
      Server -> Client: {"type": "done", "text": "Hi there!"}   (final)
      Server -> Client: {"type": "error", "text": "..."}        (error)
    """
    await ws.accept()
    logger.info("Chat WebSocket connected")

    # Generate session ID
    import uuid

    session_id = str(uuid.uuid4())[:8]

    # Conversation memory for this WebSocket session
    conversation = []

    try:
        while True:
            # Wait for user message
            raw = await ws.receive_text()
            data = json.loads(raw)

            if data.get("type") != "message":
                continue

            user_text = data.get("text", "").strip()
            if not user_text:
                continue

            logger.info(f"[{session_id}] User: {user_text[:100]}")

            # Send thinking indicator
            await ws.send_text(json.dumps({"type": "thinking", "text": ""}))

            # Get AI response with streaming
            from backend.agent import chat as agent_chat
            import functools

            async def send_delta(chunk: str):
                await ws.send_text(json.dumps({"type": "delta", "text": chunk}))

            def sync_send_delta(chunk: str):
                """Bridge from sync→async for the stream callback."""
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    asyncio.run_coroutine_threadsafe(
                        send_delta(chunk), loop
                    )
                except RuntimeError:
                    pass

            try:
                # Add user message to conversation
                conversation.append({"role": "user", "content": user_text})

                # Run the synchronous chat in a thread with full history
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None, functools.partial(
                        agent_chat,
                        messages=list(conversation),  # pass copy to avoid race
                        on_delta=sync_send_delta,
                    )
                )
                await ws.send_text(
                    json.dumps({"type": "done", "text": response or ""})
                )

                # Add assistant response to conversation
                if response and not response.startswith("Error:"):
                    conversation.append({"role": "assistant", "content": response})

                logger.info(f"[{session_id}] Response: {response[:100] if response else '(empty)'}...")
            except Exception as e:
                logger.exception(f"[{session_id}] Chat error")
                await ws.send_text(
                    json.dumps({"type": "error", "text": f"Error: {str(e)}"})
                )

    except WebSocketDisconnect:
        logger.info(f"[{session_id}] Chat WebSocket disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        try:
            await ws.send_text(json.dumps({"type": "error", "text": str(e)}))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

HOST = "127.0.0.1"
PORT = 9119


def run_server(host: str = HOST, port: int = PORT):
    """Run the Jarvis backend server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info(f"Jarvis Mark 1 server starting on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")

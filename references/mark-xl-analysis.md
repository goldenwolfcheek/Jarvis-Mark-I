# Mark-XL Analysis — Patterns for Jarvis Mark 1

**Source:** https://github.com/FatihMakes/Mark-XL (MIT License)
**Analyzed:** June 2026

## Summary

Mark-XL is a fully local AI assistant (STT → Ollama LLM → TTS) with a PyQt6 desktop HUD, 18 built-in tools, long-term memory, and multi-step agent planning/execution. It is **highly relevant** to Jarvis Mark 1.

## Top 5 Directly Reusable Components

| Component | File | Why |
|-----------|------|-----|
| **LLM client abstraction** | `core/llm_client.py` | Dual-backend (Ollama + OpenAI), streaming with sentence events, tool support |
| **Thread-safe UI facade** | `ui.py` (class `JarvisUI`) | Signals-based pattern; swap out MainWindow content, keep the API |
| **Memory manager** | `memory/memory_manager.py` | Category-based JSON memory, prompt formatting, silent save tool |
| **TTS overlap pipeline** | `main.py` / `core/tts.py` | Sentence-level streaming → TTS queue; works with any engine via adapter |
| **Tool declaration system** | `main.py` | Schema + conversion + dispatch; replace if/elif with a registry dict |

## Security Assessment

**CLEAN** — No malware, no obfuscated code, no binary blobs, no suspicious network calls. MIT licensed.
- No API keys shipped
- 99% local (only EdgeTTS optional cloud)
- Mute button for microphone
- Missing: code execution sandboxing, `computer_control` confirmation gates

## Key Architectural Patterns

### Thread-Safe UI Pattern (Critical)
```python
# PyQt signals for cross-thread communication:
_log_sig     = pyqtSignal(str)
_state_sig   = pyqtSignal(str)
# Connected in __init__:
self._log_sig.connect(self._log.append_log)
# Backend calls from ANY thread:
self.ui.write_log("text")  # emits _log_sig (thread-safe)
```

### Streaming → TTS Overlap
```python
for event in call_llm_stream(messages, tools):
    if event["type"] == "sentence":
        self.speak(event["text"])  # Queue immediately
    elif event["type"] == "done":
        # Process tool_calls
```
Sentence splitting regex: `(?<=[.!?])\s+|(?<=\n)\s*\n`

### Memory Injection
```python
def _build_system_prompt(self):
    sys_p   = _load_system_prompt()
    memory  = load_memory()
    mem_str = format_memory_for_prompt(memory)
    time_ctx = f"[CURRENT DATE & TIME]\nRight now it is: ..."
    return "\n\n".join([sys_p, mem_str, time_ctx])
```

### 6-Category Memory Schema
```python
memory = {
    "identity": {}, "preferences": {}, "projects": {},
    "relationships": {}, "wishes": {}, "notes": {},
}
# Each entry: {"value": str, "updated": "YYYY-MM-DD"}
```

## Tool System
- 18 tools declared in Gemini-style schema
- Converted to OpenAI/Ollama format at runtime
- Special tools: `save_memory` → silent (no speech), `web_search`/`screen_process` → results re-fed to LLM
- Max 6 tool rounds per user message

## Startup Bootstrap
```python
_BASE_PKGS = [("PyQt6","PyQt6"), ("psutil","psutil"), ...]
def _bootstrap():
    need = [pkg for mod, pkg in _BASE_PKGS if importlib.find_spec(mod) is None]
    if need:
        subprocess.run([sys.executable, "-m", "pip", "install", *need])
        os.execv(...)  # Restart
```

## Future Plans for Jarvis Mark 1
1. **Phase 1:** Port `core/llm_client.py` for local Ollama support alongside cloud APIs
2. **Phase 2:** Port `memory/memory_manager.py` for persistent memory
3. **Phase 3:** Build PyQt6 desktop UI using Mark-XL's pattern
4. **Phase 4:** Port action/tool system with dict-based registry
5. **Phase 5:** Add code execution sandbox and computer control gates

"""Agent — makes direct OpenAI-compatible API calls using Jarvis' own config.

Handles both authenticated (paid models) and unauthenticated (free models) API calls.
If no API key is configured, no auth headers are sent — some providers like
OpenCode Zen allow free model access without authentication.

Cross-platform: this module uses only Python standard library (urllib, json,
logging) and is fully cross-platform — no OS-specific code.
"""

import json
import logging
from urllib import request as urllib_request
from typing import Callable

logger = logging.getLogger("jarvis.agent")


def _get_config():
    """Load provider config from Jarvis settings."""
    from backend.config import load_config
    return load_config()


def _get_headers(api_key: str) -> dict:
    """Build request headers. Only adds Authorization if api_key is set.

    Sets a custom User-Agent because some providers (e.g. OpenCode Zen)
    block Python's default urllib User-Agent.
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Jarvis-Mark-1/1.0",
    }
    if api_key and api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    else:
        logger.info("No API key set — making unauthenticated request (free model fallback)")
    return headers


def _normalize_url(base_url: str) -> str:
    """Build a proper chat completions URL from the base URL."""
    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    return url


def _call_openai_compatible(
    messages: list,
    model: str,
    base_url: str,
    api_key: str,
    on_delta: Callable = None,
    max_tokens: int = 4096,
    tools: list = None,
    stream: bool = True,
) -> dict:
    """Make a streaming or non-streaming chat completion call.

    Returns dict with:
      - "content": full response text (or empty if tool_calls present)
      - "tool_calls": list of tool call dicts if any, else []
      - "error": error message if failed, else None
    """
    chat_url = _normalize_url(base_url)

    body_data = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "max_tokens": max_tokens,
    }
    if tools:
        body_data["tools"] = tools
        body_data["tool_choice"] = "auto"

    req = urllib_request.Request(
        chat_url,
        data=json.dumps(body_data).encode("utf-8"),
        headers=_get_headers(api_key),
        method="POST",
    )

    logger.info(f"POST {chat_url} model={model} tools={bool(tools)} stream={stream}")

    if stream:
        # --- Streaming mode ---
        full_text = ""
        collected_tool_calls = []
        try:
            resp = urllib_request.urlopen(req, timeout=120)
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or line.startswith(":"):
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})

                        # Text content
                        content = delta.get("content", "")
                        if content:
                            full_text += content
                            if on_delta:
                                try:
                                    on_delta(content)
                                except Exception:
                                    pass

                        # Tool calls (during streaming)
                        tc_list = delta.get("tool_calls", [])
                        for tc in tc_list:
                            idx = tc.get("index", 0)
                            # Accumulate tool call fragments
                            while len(collected_tool_calls) <= idx:
                                collected_tool_calls.append({
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                })
                            if tc.get("id"):
                                collected_tool_calls[idx]["id"] += tc["id"]
                            if tc.get("function", {}).get("name"):
                                collected_tool_calls[idx]["function"]["name"] += tc["function"]["name"]
                            if tc.get("function", {}).get("arguments"):
                                collected_tool_calls[idx]["function"]["arguments"] += tc["function"]["arguments"]
                    except json.JSONDecodeError:
                        continue

            return {
                "content": full_text,
                "tool_calls": collected_tool_calls if collected_tool_calls else [],
                "error": None,
            }

        except urllib_request.HTTPError as e:
            code = e.code
            detail = ""
            try:
                detail = e.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass

            if code == 401:
                msg = f"API key is invalid (401). Check Settings → Provider."
            elif code == 403:
                msg = f"Access denied (403). Your API key may lack access to model '{model}'."
            elif code == 404:
                msg = f"Endpoint not found (404). Check base_url."
            else:
                msg = f"HTTP {code}: {detail or str(e)}"
            logger.error(f"Agent API error: {msg}")
            return {"content": "", "tool_calls": [], "error": f"Error: {msg}"}

        except urllib.request.URLError as e:
            msg = f"Connection failed: {e.reason}."
            return {"content": "", "tool_calls": [], "error": f"Error: {msg}"}

        except Exception as e:
            logger.exception("Agent API call failed")
            return {"content": "", "tool_calls": [], "error": f"Error: {str(e)}"}

    else:
        # --- Non-streaming mode (used for tool detection) ---
        try:
            resp = urllib_request.urlopen(req, timeout=120)
            body = json.loads(resp.read().decode("utf-8"))
            choice = body.get("choices", [{}])[0]
            msg = choice.get("message", {})

            return {
                "content": msg.get("content", "") or "",
                "tool_calls": msg.get("tool_calls", []) or [],
                "error": None,
            }

        except urllib_request.HTTPError as e:
            code = e.code
            detail = ""
            try:
                detail = e.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            msg = f"HTTP {code}: {detail or str(e)}"
            return {"content": "", "tool_calls": [], "error": f"Error: {msg}"}

        except Exception as e:
            return {"content": "", "tool_calls": [], "error": f"Error: {str(e)}"}


def chat(message: str = None, messages: list = None, system_prompt: str = None, on_delta: Callable = None) -> str:
    """Send a message(s) with tool support and get a streaming response.

    Supports function calling: when the AI requests tool use, the tools
    are executed and results fed back before returning the final response.

    Args:
        message: Single user message.
        messages: Full conversation history.
        system_prompt: Optional system instruction.
        on_delta: Called with each text chunk during streaming.
    Returns:
        The full response text, or an error string starting with "Error:".
    """
    from backend.tools import TOOLS, SYSTEM_PROMPT as TOOL_SYSTEM_PROMPT, execute_tool_call

    cfg = _get_config()
    base_url = cfg.get("base_url", "")
    model = cfg.get("model", "")
    api_key = cfg.get("api_key", "") or ""

    if not base_url:
        return "Error: No base_url configured."
    if not model:
        return "Error: No model configured."

    # Build conversation history
    effective_system = system_prompt or TOOL_SYSTEM_PROMPT
    if messages is None:
        messages = []
        messages.append({"role": "system", "content": effective_system})
        if message:
            messages.append({"role": "user", "content": message})
    elif system_prompt:
        messages = [{"role": "system", "content": effective_system}] + messages

    MAX_TOOL_TURNS = 6

    for turn in range(MAX_TOOL_TURNS):
        # All turns are non-streaming for correct tool detection
        result = _call_openai_compatible(
            messages=messages,
            model=model,
            base_url=base_url,
            api_key=api_key,
            on_delta=None,
            tools=TOOLS,
            stream=False,
        )

        if result["error"]:
            return result["error"]

        content = result.get("content", "") or ""
        native_tool_calls = result.get("tool_calls", []) or []

        # Check for XML-style tool calls in content
        xml_tool_calls = []
        if not native_tool_calls and content:
            from backend.tools import parse_xml_tool_calls as _parse_xml
            xml_tool_calls = _parse_xml(content)

        all_tool_calls = native_tool_calls or xml_tool_calls

        if not all_tool_calls:
            # No tools needed — this is the final response.
            # Strip any XML artifacts and deliver via on_delta.
            from backend.tools import strip_xml_tool_calls as _strip_xml
            clean = _strip_xml(content)
            if clean:
                if on_delta:
                    on_delta(clean)
                return clean
            return content or "(empty response)"

        # Execute tool calls
        for tc in all_tool_calls:
            fn_name = tc.get("function", {}).get("name", "?")
            logger.info(f"Tool call: {fn_name}")

            # Execute tool
            tool_result = execute_tool_call(tc)
            logger.info(f"Tool result: {tool_result[:200]}")

            # Add messages in the right format for this model
            if native_tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tc],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": tool_result,
                })
            else:
                messages.append({
                    "role": "user",
                    "content": f"Tool '{fn_name}' returned:\n{tool_result[:800]}",
                })

    return "Error: Too many tool operations."


def fetch_models(base_url: str, api_key: str = "") -> list:
    """Fetch available models from a provider's /v1/models endpoint."""
    models_url = base_url.rstrip("/")
    if models_url.endswith("/v1"):
        models_url += "/models"
    elif not models_url.endswith("/models"):
        if models_url.endswith("/chat/completions"):
            models_url = models_url.replace("/chat/completions", "/models")
        else:
            models_url += "/models"

    req = urllib_request.Request(
        models_url,
        headers=_get_headers(api_key),
        method="GET",
    )

    try:
        resp = urllib_request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode("utf-8"))
        models = data.get("data", [])
        return [m["id"] for m in models if "id" in m]
    except Exception as e:
        logger.warning(f"Failed to fetch models from {models_url}: {e}")
        return []


def reset_agent():
    """Clear any cached state (no-op for this simple client)."""
    pass

"""Tool definitions and execution for Jarvis Mark 1.

Provides tools for file operations, web search/fetch, app launching,
and the system prompt that tells the AI about its capabilities.
"""

import json
import logging
import os
import re
import shlex
import subprocess
import urllib.request
import urllib.parse

logger = logging.getLogger("jarvis.tools")

# ---------------------------------------------------------------------------
# Tool Schema Definitions (OpenAI-compatible function calling format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a file at the specified path with the given content. Overwrites if exists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full or relative file path (e.g., C:\\Users\\User\\Desktop\\note.txt or ~/Desktop/note.txt)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file at the specified path",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path to the file"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and read the text content of a web page. Returns the page title and body text (stripped of HTML).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL to fetch (e.g., https://example.com/page)"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for a query. Returns a summary and relevant links from the web.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an application on the computer. Supports common apps like calculator, notepad, browser, paint, command prompt, and more. For uncertified apps, provide the exact name or path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app": {
                        "type": "string",
                        "description": "Application name (e.g., 'calculator', 'notepad', 'chrome', 'explorer') or full executable path"
                    }
                },
                "required": ["app"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_apps",
            "description": "List all user-registered applications that can be launched. Use this to discover what apps are configured.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute a shell command on the computer. Use with caution — only for safe, read-only operations or when the user explicitly asks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    },
]

# Default apps map for quick launch.
# NOTE: These are Windows-only paths (C:\Program Files\...).  On macOS or
# Linux the executable names and locations will differ.  If you port this
# project to another OS, replace the paths below or add platform branching.
DEFAULT_APPS = {
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "notepad": "notepad.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "mozilla firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "terminal": "cmd.exe",
    "powershell": "powershell.exe",
    "paint": "mspaint.exe",
    "microsoft paint": "mspaint.exe",
    "task manager": "taskmgr.exe",
    "control panel": "control.exe",
    "settings": "ms-settings:",
    "snipping tool": "snippingtool.exe",
}


def _safe_path(path: str) -> str:
    """Expand ~/ and resolve environment variables."""
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    return os.path.abspath(path)


# ---------------------------------------------------------------------------
# Tool Execution
# ---------------------------------------------------------------------------

def create_file(path: str, content: str) -> str:
    """Create or overwrite a file with content."""
    try:
        path = _safe_path(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Created file: {path} ({len(content)} chars)")
        return f"✓ File created: {path} ({len(content)} characters written)"
    except Exception as e:
        logger.error(f"create_file failed: {e}")
        return f"✗ Error creating file: {str(e)}"


def read_file(path: str) -> str:
    """Read a file and return its contents."""
    try:
        path = _safe_path(path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Read file: {path} ({len(content)} chars)")
        return content[:50000]  # Limit to 50K chars
    except Exception as e:
        logger.error(f"read_file failed: {e}")
        return f"✗ Error reading file: {str(e)}"


def web_fetch(url: str) -> str:
    """Fetch a web page and extract text content."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "JarvisMark1/1.0 (AI Assistant; compatible)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        
        # Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else "No title"
        
        # Strip HTML tags to get plain text
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        text = text[:10000]  # Limit to 10K chars
        
        result = f"Title: {title}\n\n{text[:10000]}"
        logger.info(f"Fetched URL: {url} ({len(html)} bytes → {len(text)} chars text)")
        return result
    except Exception as e:
        logger.error(f"web_fetch failed: {e}")
        return f"✗ Error fetching {url}: {str(e)}"


def web_search(query: str) -> str:
    """Search the web using DuckDuckGo (free, no key needed). Falls back to HTML search."""
    try:
        # First try: DuckDuckGo Instant Answer API
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "JarvisMark1/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        parts = []
        
        if data.get("AbstractText"):
            parts.append(f"Summary: {data['AbstractText']}")
            if data.get("AbstractSource"):
                parts.append(f"Source: {data['AbstractSource']}")
        if data.get("Answer"):
            parts.append(f"Answer: {data['Answer']}")
        if data.get("RelatedTopics"):
            topics = []
            for t in data["RelatedTopics"][:8]:
                if isinstance(t, dict):
                    text = t.get("Text", "")
                    if text:
                        topics.append(f"• {text}")
                elif isinstance(t, list):
                    for st in t[:3]:
                        text = st.get("Text", "") if isinstance(st, dict) else ""
                        if text:
                            topics.append(f"• {text}")
            if topics:
                parts.append("Related:\n" + "\n".join(topics[:8]))
        if data.get("Results"):
            for r in data["Results"][:3]:
                if isinstance(r, dict) and r.get("Text"):
                    parts.append(f"• {r['Text']}")
        
        if parts:
            result = "\n\n".join(parts)
            logger.info(f"Web search (instant answer): '{query}' → {len(result)} chars")
            return result[:8000]
        
        # Second try: DuckDuckGo Lite HTML search
        logger.info(f"DuckDuckGo instant answer empty — trying HTML search for: {query}")
        html_url = "https://html.duckduckgo.com/html/"
        post_data = urllib.parse.urlencode({"q": query}).encode()
        html_req = urllib.request.Request(
            html_url,
            data=post_data,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with urllib.request.urlopen(html_req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        
        # Extract result snippets from HTML
        results = []
        # Find result blocks: class="result__snippet"
        snippets = re.findall(
            r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        bodies = re.findall(
            r'class="result__snippet[^"]*"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        
        for i, (url_match, title_match) in enumerate(snippets[:5]):
            clean_title = re.sub(r'<[^>]+>', '', title_match).strip()
            clean_url = url_match.replace('//duckduckgo.com/l/?uddg=', '').split('&')[0]
            clean_url = urllib.parse.unquote(clean_url)
            snippet = ""
            if i < len(bodies):
                snippet = re.sub(r'<[^>]+>', '', bodies[i]).strip()
            results.append(f"{i+1}. {clean_title}\n   {clean_url}\n   {snippet[:200]}")
        
        if results:
            result = "\n\n".join(results)
            logger.info(f"Web search (HTML): '{query}' → {len(result)} chars")
            return result[:8000]
        
        return "No search results found."
    except Exception as e:
        logger.error(f"web_search failed: {e}")
        return f"✗ Search failed for '{query}': {str(e)}"


def open_app(app: str) -> str:
    """Open an application by name."""
    try:
        # Check registered apps first
        from backend.config import load_registered_apps
        registered = load_registered_apps()
        for reg_app in registered:
            if reg_app.get("name", "").lower() == app.lower():
                cmd = reg_app.get("command", "")
                args = reg_app.get("args", "")
                if args:
                    cmd = f"{cmd} {args}"
                subprocess.Popen(cmd, shell=True)
                logger.info(f"Launched registered app: {app}")
                return f"✓ Launched {app}"

        # Check default apps map only — never fall through to raw input
        cmd = DEFAULT_APPS.get(app.lower())
        if cmd is None:
            return f"✗ Unknown app '{app}'. Use list_apps to see available apps."
        subprocess.Popen(cmd, shell=True)
        logger.info(f"Launched app: {app} → {cmd}")
        return f"✓ Opened {app}"
    except Exception as e:
        logger.error(f"open_app failed: {e}")
        return f"✗ Error opening {app}: {str(e)}"


def list_apps() -> str:
    """List all registered applications."""
    try:
        from backend.config import load_registered_apps
        apps = load_registered_apps()
        if not apps:
            return "No registered apps configured. You can register apps in Settings."
        
        lines = [f"You have {len(apps)} registered app(s):"]
        for a in apps:
            name = a.get("name", "?")
            cmd = a.get("command", "?")
            lines.append(f"  • {name} → {cmd}")
        return "\n".join(lines)
    except Exception as e:
        return f"✗ Error listing apps: {str(e)}"



# Whitelist of safe, read-only shell commands.
# Supports BOTH Windows commands (dir, type, findstr, ipconfig, systeminfo, ...)
# AND Unix commands (ls, pwd, ...) so the same whitelist works regardless of
# which OS the user is running.  The shell will simply reject commands not on
# this list.
SAFE_COMMANDS = {
    "dir", "ls", "echo", "type", "find", "findstr", "where",
    "ipconfig", "ping", "nslookup", "tracert", "netstat",
    "systeminfo", "tasklist", "whoami", "ver", "date", "time",
    "chcp", "cd", "pwd", "help",
}

def execute_command(command: str) -> str:
    """Execute a shell command (limited to safe, read-only operations)."""
    # Parse into parts — reject shell=True entirely
    try:
        parts = shlex.split(command)
    except Exception:
        return "✗ Invalid command syntax"
    if not parts:
        return "✗ Empty command"

    cmd_name = os.path.basename(parts[0]).lower()
    if cmd_name not in SAFE_COMMANDS:
        return f"✗ Command '{cmd_name}' is not in the allowed whitelist"

    try:
        result = subprocess.run(
            parts,  # No shell=True — list form prevents injection
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout[:5000]
        if result.stderr:
            output += f"\nSTDERR: {result.stderr[:2000]}"
        return output or "(Command completed with no output)"
    except subprocess.TimeoutExpired:
        return "✗ Command timed out after 30 seconds"
    except Exception as e:
        return f"✗ Command error: {str(e)}"


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY = {
    "create_file": create_file,
    "read_file": read_file,
    "web_fetch": web_fetch,
    "web_search": web_search,
    "open_app": open_app,
    "list_apps": list_apps,
    "execute_command": execute_command,
}


def parse_xml_tool_calls(content: str) -> list:
    """Parse XML-style tool calls from model output.
    
    Only matches if content contains a <tool_calls> wrapper tag,
    to avoid mistaking random XML in the model's response for tool calls.
    
    Some models (like the free OpenCode Zen model) don't support native
    OpenAI function calling. Instead they output XML like:
    
        <tool_calls>
        <invoke name="web_search">
        <parameter name="query" string="true">Wikipedia founding</parameter>
        </invoke>
        </tool_calls>
    
    Returns a list of tool call dicts compatible with execute_tool_call().
    """
    import re as _re
    
    # Only parse if content has a <tool_calls> wrapper
    if not _re.search(r'<tool_calls>', content, _re.IGNORECASE):
        return []
    
    tool_calls = []
    # Find all <invoke name="..."> blocks
    pattern = _re.compile(r'<invoke\s+name="([^"]+)"[^>]*>(.*?)</invoke>', _re.DOTALL)
    
    for idx, match in enumerate(pattern.finditer(content)):
        fn_name = match.group(1).strip()
        body = match.group(2).strip()
        
        # Extract parameters: <parameter name="key" ...>value</parameter>
        param_pattern = _re.compile(r'<parameter\s+name="([^"]+)"[^>]*>(.*?)</parameter>', _re.DOTALL)
        args = {}
        for pm in param_pattern.finditer(body):
            key = pm.group(1).strip()
            val = pm.group(2).strip()
            args[key] = val
        
        # Convert to standard tool call format
        tool_calls.append({
            "id": f"call_xml_{idx}",
            "type": "function",
            "function": {
                "name": fn_name,
                "arguments": json.dumps(args),
            }
        })
    
    return tool_calls


def strip_xml_tool_calls(content: str) -> str:
    """Remove XML tool call blocks from content, leaving only natural text."""
    import re as _re
    cleaned = _re.sub(r'<tool_calls>.*?</tool_calls>', '', content, flags=_re.DOTALL)
    cleaned = _re.sub(r'<invoke[^>]*>.*?</invoke>', '', cleaned, flags=_re.DOTALL)
    cleaned = _re.sub(r'<parameter[^>]*>.*?</parameter>', '', cleaned, flags=_re.DOTALL)
    return cleaned.strip()


def execute_tool_call(tool_call: dict) -> str:
    """Execute a single tool call from the API response.
    
    Args:
        tool_call: A tool call object with 'function' containing 'name' and 'arguments'
    
    Returns:
        Result string from the tool execution
    """
    fn_name = tool_call.get("function", {}).get("name", "")
    fn_args_raw = tool_call.get("function", {}).get("arguments", "{}")
    
    try:
        fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
    except json.JSONDecodeError:
        return f"✗ Error: Invalid arguments JSON for {fn_name}"
    
    if fn_name not in TOOL_REGISTRY:
        return f"✗ Unknown tool: {fn_name}"
    
    logger.info(f"Executing tool: {fn_name}({fn_args})")
    try:
        result = TOOL_REGISTRY[fn_name](**fn_args)
        return str(result)
    except TypeError as e:
        return f"✗ Tool {fn_name} error: {str(e)}"
    except Exception as e:
        return f"✗ Tool {fn_name} failed: {str(e)}"


# ---------------------------------------------------------------------------
# Enhanced System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), an AI assistant created for the user. You are based on the Iron Man movies' Jarvis AI.

You have access to the following tools and capabilities:

1. **File Operations** — You can create files, read files, and write content anywhere on the user's computer.
2. **Web Access** — You can fetch web pages and search the web for information.
3. **App Control** — You can open applications on the user's computer (calculator, notepad, browser, etc.) and list registered apps.
4. **Command Execution** — You can run shell commands (limited for safety).

When the user asks you to do something that requires these capabilities, use the appropriate tool. After using a tool, explain what you did and the result.

Always be helpful, concise, and use a professional but friendly tone. Address the user as "sir" or by name if you know it. Reference the current date and time when relevant.

Your knowledge cutoff is the current date. Use web search to get up-to-date information when needed.
"""

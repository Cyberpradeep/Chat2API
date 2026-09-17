# ChatGPT Web-to-API Bridge (v2.0)

[![Status](https://img.shields.io/badge/Status-Operational-green.svg)]()
[![API Spec](https://img.shields.io/badge/API-OpenAI%20v1%20Compatible-blue.svg)]()
[![Architecture](https://img.shields.io/badge/Architecture-Modular-orange.svg)]()
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Local-purple.svg)]()
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)]()

A lightweight, local REST API and drop-in OpenAI-compatible bridge for the ChatGPT web client. Built with Playwright, FastAPI, and an extensible provider abstraction.

---

## Overview

ChatGPT Web-to-API Bridge exposes standard OpenAI-compatible endpoints (`/v1/chat/completions`, `/v1/models`) backed by your existing ChatGPT web subscription. All execution is handled entirely on your local machine using an automated, persistent Chromium browser context.

Unlike cloud-based relay solutions:
- **No Third-Party Relays**: All traffic remains strictly on `127.0.0.1`.
- **Full Agentic Capabilities**: Supports system instructions (`role: "system"`) and structured tool calling (`tools=[...]`), enabling multi-turn autonomous AI agent loops.
- **Modern ChatGPT Feature Support**: Access Think Mode (deep reasoning), live Web Search, Deep Research, and multimodal file/image attachments.
- **Anti-Throttling Architecture**: Built-in Chromium flags prevent execution pauses when the browser window is minimized or running in the background.

---

## Architectural Comparison

| Capability | Cloud Relays (e.g., ApiBeam) | ChatGPT Web-to-API Bridge (v2.0) |
| :--- | :--- | :--- |
| **Data Privacy** | Forwarded through third-party servers | 100% Local (`127.0.0.1`) |
| **System Prompts (`role: "system"`)** | Not supported or ignored | Supported (framed and persona-enforced) |
| **Tool Calling (`tools=[...]`)** | Not supported | Supported (returns structured OpenAI JSON) |
| **Multi-Turn Agent Workflows** | Not supported | Supported (battle-tested with official OpenAI SDK) |
| **Interface Compatibility** | Fragile against UI changes | Resilient multi-tier selector architecture |
| **Reasoning / Think Mode** | Not exposed | Supported via parameter toggle |
| **Multimodal Vision & Files** | Rarely supported | Supported (local files, PDFs, base64 images) |
| **Background Execution** | Freezes when minimized | Unthrottled via OS-level Chromium flags |
| **Operational Cost** | Subscription / token-based | Free and open source |

---

## Repository Structure

```
d:\chatgpt_api\
├── config/
│   ├── settings.py              # Environment configuration loader (.env)
│   └── selectors.py             # Multi-tier DOM selectors for the ChatGPT UI
├── core/
│   ├── browser_manager.py       # Persistent Chromium lifecycle and stealth flags
│   ├── prompt_compiler.py       # System prompt compiler and tool-call parser
│   └── file_uploader.py         # File attachment and base64 vision decoder
├── providers/
│   ├── base_provider.py         # Abstract interface for LLM web providers
│   └── chatgpt/
│       ├── provider.py          # Primary ChatGPT automation provider
│       ├── toggles.py           # UI state controllers (Think, Search, Deep Research)
│       └── extractor.py         # Markdown extractor for answers, thoughts, and citations
├── server/
│   ├── app.py                   # FastAPI initialization, CORS, and lifespan management
│   ├── routes.py                # Endpoints for /api/chat and OpenAI /v1
│   └── schemas.py               # Pydantic models for validation and responses
├── tests/                       # Dedicated test suite
│   ├── test_client.py           # CLI test client with feature flag controls
│   ├── test_openai_sdk.py       # Official OpenAI Python SDK compatibility test
│   ├── test_system_and_tools.py # System instruction and function calling test
│   └── test_full_agent_loop.py  # Multi-turn autonomous agent test with local tools
├── user_data/                   # Persistent authenticated browser session directory
├── temp_uploads/                # Staging folder for temporary file/image uploads
├── .env                         # Local runtime environment variables
├── login_helper.py              # Guided authentication utility
├── run.py                       # Application entry point and server launcher
├── requirements.txt             # Project dependencies
└── README.md                    # Project documentation
```

---

## Prerequisites and Installation

### 1. Requirements
- Python 3.10 or higher
- Google Chrome or Chromium
- An active ChatGPT account

### 2. Setup Environment
Clone the repository and install dependencies:

```powershell
pip install -r requirements.txt
playwright install chromium
```

---

## Quickstart

### Step 1: Authenticate Session (One-Time)
Run the authentication helper to log into ChatGPT:

```powershell
python login_helper.py
```

1. A browser window opens navigating to `https://chatgpt.com`.
2. Complete login with your account (and any Cloudflare or 2FA checks).
3. Once the main prompt interface appears, return to the terminal and press `[Enter]`.
4. Your authenticated session is saved to `./user_data/`. You will not need to log in again.

### Step 2: Start the API Server
Launch the FastAPI server using the entry point:

```powershell
python run.py
```

Default endpoints:
- API Server: `http://127.0.0.1:8088`
- OpenAI Base URL: `http://127.0.0.1:8088/v1`
- Interactive OpenAPI Docs: `http://127.0.0.1:8088/docs`
- Health Status: `http://127.0.0.1:8088/api/status`

---

## Integration and Usage

### 1. Official OpenAI Python SDK
Set `base_url` to `http://127.0.0.1:8088/v1`. Any valid `api_key` string can be supplied since authentication is handled locally.

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8088/v1",
    api_key="local"
)

response = client.chat.completions.create(
    model="chatgpt",
    messages=[
        {"role": "system", "content": "You are a concise technical writer."},
        {"role": "user", "content": "Explain asynchronous programming in two sentences."}
    ]
)

print(response.choices[0].message.content)
```

---

### 2. Structured Function Calling (Tool Calls)
Define functions using standard JSON schema specifications:

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8088/v1", api_key="local")

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Fetch current trading price for a stock ticker symbol.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Ticker symbol, e.g. NVDA, MSFT"}
                },
                "required": ["ticker"]
            }
        }
    }
]

response = client.chat.completions.create(
    model="chatgpt",
    messages=[
        {"role": "user", "content": "What is the current stock price of Microsoft (MSFT)?"}
    ],
    tools=tools
)

choice = response.choices[0]
if choice.finish_reason == "tool_calls":
    for tool_call in choice.message.tool_calls:
        print(f"Function: {tool_call.function.name}")
        print(f"Arguments: {tool_call.function.arguments}")
```

---

### 3. Native REST API (`/api/chat`)
For applications needing direct access to UI toggles, citations, or thought traces:

```bash
curl -X POST http://127.0.0.1:8088/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Summarize latest developments in solid-state battery research.",
    "think": true,
    "web_search": true,
    "deep_research": false,
    "files": [],
    "new_chat": false
  }'
```

Response schema:
```json
{
  "response": "Solid-state battery research in 2025-2026 has focused on...",
  "thought_process": "Searching academic preprints and recent battery symposiums...",
  "sources": [
    "https://example.com/battery-research-2025"
  ],
  "model": "chatgpt",
  "finish_reason": "stop"
}
```

---

## Test Suite

All test scripts are located in [`tests/`](file:///d:/chatgpt_api/tests) and can be executed independently.

### Interactive CLI Client
Tests manual prompt execution, attachments, and toggle behaviors:
```powershell
# Standard prompt
python tests/test_client.py "Explain gravitational lensing."

# Reasoning / Think Mode
python tests/test_client.py "Solve this scheduling puzzle..." --think

# Live Web Search
python tests/test_client.py "What are the latest semiconductor news headlines?" --search

# File Attachment
python tests/test_client.py "Analyze this log file" --file "path/to/logfile.txt"

# New Session
python tests/test_client.py "Start fresh session" --new
```

### OpenAI SDK Compatibility Test
Validates models listing and basic chat completion:
```powershell
python tests/test_openai_sdk.py
```

### System Instruction & Function Calling Test
Validates prompt persona enforcement and structured tool generation:
```powershell
python tests/test_system_and_tools.py
```

### Multi-Turn Autonomous Agent Loop Test
Simulates an autonomous cybersecurity incident responder that queries local Python functions over multiple conversation turns to produce a synthesized investigation report:
```powershell
python tests/test_full_agent_loop.py
```

---

## Configuration Reference

Configuration is managed via [`.env`](file:///d:/chatgpt_api/.env) with the following parameters:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `HOST` | string | `127.0.0.1` | Network interface to bind the API server. |
| `PORT` | integer | `8088` | Port number for the API server. |
| `HEADLESS` | boolean | `false` | Run browser headlessly (`true`) or visibly (`false`). Visible mode is recommended to avoid Cloudflare bot detection. |
| `BROWSER_CHANNEL` | string | `chrome` | Browser channel (`chrome` uses local Chrome, falls back to Playwright Chromium). |
| `TIMEOUT_SECONDS` | integer | `180` | Maximum timeout in seconds per completion request. |

---

## Background Throttling Prevention

Modern operating systems throttle resource allocation to background and minimized browser windows, which can pause JavaScript execution and network streaming. 

To ensure consistent performance during long generations, the browser context initializes with the following Chromium command-line flags:
- `--disable-background-timer-throttling`
- `--disable-backgrounding-occluded-windows`
- `--disable-renderer-backgrounding`
- `--disable-component-update`

The browser window may be minimized or placed on an alternate virtual desktop without interrupting active completions.

---

## Troubleshooting

### Browser authentication expired
If the server returns status errors indicating an unauthenticated state, re-run:
```powershell
python login_helper.py
```
Log in again and press `[Enter]` to update the session files in `./user_data/`.

### Cloudflare verification prompts
If Cloudflare presents a verification challenge, ensure `HEADLESS=false` in `.env`. Complete the verification manually once in the visible browser; the state will persist for subsequent requests.

### Port conflict
If port 8088 is occupied by another process, update `PORT` in `.env` to any available port (e.g., `8090`).

---

## License

MIT License. Developed for local automation, research, and self-hosted AI agent development.

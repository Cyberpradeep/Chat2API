# ChatGPT Modular Web-to-API Engine (v2.0)

A lightweight, 100% local REST API and **drop-in OpenAI API replacement** wrapping the ChatGPT web client. Built with **Playwright**, **FastAPI**, and an extensible provider abstraction.

## ✨ Features

- **100% Local & Private**: No cloud relays (unlike ApiBeam). All traffic stays on `127.0.0.1`.
- **Drop-in OpenAI SDK Compatibility**: Point the official `openai` Python or JavaScript library directly at `http://127.0.0.1:8088/v1`.
- **Think Mode Support**: Toggle deep reasoning on and off via API parameters.
- **Web Search & Deep Research**: Toggle live web search or comprehensive research reports via the `+` menu.
- **Multimodal Attachments**: Send local files, photos, PDFs, or base64 vision images.
- **Anti-Throttling Chromium Engine**: Runs with OS-level flags so generation never freezes when minimized.
- **Persistent Profile**: Log in once; your session stays authenticated in `./user_data`.
- **Modular Base Architecture**: Ready for Claude and Gemini providers in the future.

---

## 📁 Modular Project Structure

```
d:\chatgpt_api\
├── config/
│   ├── settings.py           # Configuration loaded from .env
│   └── selectors.py          # Centralized DOM selectors for ChatGPT
├── core/
│   ├── browser_manager.py    # Persistent Chromium context & anti-throttling flags
│   └── file_uploader.py      # Base64 decoder & file attachment watchdog
├── providers/
│   ├── base_provider.py      # Abstract interface for all AI providers
│   └── chatgpt/
│       ├── provider.py       # Core ChatGPT automation provider
│       ├── toggles.py        # Think, Web Search, and Deep Research toggles
│       └── extractor.py      # Response, citations, and thought process extractor
├── server/
│   ├── app.py                # FastAPI app setup with CORS
│   ├── routes.py             # Both /api/chat and /v1/chat/completions
│   └── schemas.py            # Pydantic schemas
├── user_data/                # Authenticated session files
├── .env                      # Simple config (PORT, HEADLESS, etc.)
├── run.py                    # 1-Click Master Launcher
├── test_client.py            # Interactive CLI test client
├── test_openai_sdk.py        # Official OpenAI SDK verification
└── README.md                 # Documentation
```

---

## 🚀 Quickstart

### 1. Start the API Server
```powershell
python run.py
```
- Server starts on **`http://127.0.0.1:8088`**.
- Interactive Swagger documentation: **[http://127.0.0.1:8088/docs](http://127.0.0.1:8088/docs)**
- OpenAI Base URL: **`http://127.0.0.1:8088/v1`**

---

### 2. Test with the Interactive Client

```powershell
# Basic Prompt
python test_client.py "Explain gravity in one sentence"

# Enable Think Mode (Reasoning)
python test_client.py "Solve this logic riddle" --think

# Enable Web Search
python test_client.py "What are today's top tech headlines?" --search

# Attach a File or Photo
python test_client.py "Summarize this document" --file "path/to/report.pdf"

# Start a Clean Chat
python test_client.py "Hello!" --new
```

---

### 3. Use with the Official OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8088/v1",
    api_key="not-needed-local"
)

response = client.chat.completions.create(
    model="chatgpt",
    messages=[
        {"role": "user", "content": "What is the speed of light? Answer in 5 words."}
    ]
)

print(response.choices[0].message.content)
```

---

### 4. Direct HTTP / cURL Usage

```bash
curl -X POST http://127.0.0.1:8088/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum superposition",
    "think": true,
    "web_search": false,
    "deep_research": false,
    "files": []
  }'
```

---

## ⚙️ Configuration (`.env`)

```ini
# Server Settings
HOST=127.0.0.1
PORT=8088

# Browser Options
HEADLESS=false                 # Set to false for visibility & maximum Cloudflare bypass
BROWSER_CHANNEL=chrome         # Uses installed Chrome, falls back to bundled Chromium
TIMEOUT_SECONDS=180
```

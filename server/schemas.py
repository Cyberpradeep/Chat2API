"""
Pydantic schemas for the REST API and OpenAI SDK compatibility.
Includes full support for System Instructions and Tool / Function Calls.
"""

import time
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

# --- Custom API Schemas ---

class ChatRequest(BaseModel):
    prompt: str = Field(..., description="The prompt or question to send", min_length=1)
    system_prompt: Optional[str] = Field(None, description="System instructions to guide persona, rules, and output style")
    think: bool = Field(False, description="Enable Think Mode (Reasoning)")
    web_search: bool = Field(False, description="Enable live Web search via '+' menu")
    deep_research: bool = Field(False, description="Enable Deep research via '+' menu")
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="List of tool definitions for function calling")
    files: List[str] = Field(default_factory=list, description="List of local file paths or base64 data URLs")
    new_chat: bool = Field(False, description="Start a fresh conversation before sending")
    timeout_seconds: int = Field(180, description="Max seconds to wait for generation", ge=10, le=600)


class ChatResponse(BaseModel):
    prompt: str
    response: Optional[str] = None
    thought_process: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    sources: List[str] = Field(default_factory=list)
    toggles: Dict[str, Any] = Field(default_factory=dict)
    finish_reason: str = "stop"
    status: str = "success"


class StatusResponse(BaseModel):
    browser_ready: bool
    current_url: Optional[str] = None
    input_ready: bool
    profile_dir: str


# --- OpenAI SDK Compatibility Schemas ---

class OpenAIMessage(BaseModel):
    role: str
    content: Optional[Union[str, List[Dict[str, Any]]]] = ""
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class OpenAICompletionRequest(BaseModel):
    messages: List[OpenAIMessage]
    model: Optional[str] = Field("chatgpt", description="Accepted for SDK compatibility, model is unified")
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    think: Optional[bool] = False
    web_search: Optional[bool] = False
    deep_research: Optional[bool] = False
    stream: Optional[bool] = False
    temperature: Optional[float] = 1.0


class OpenAIChoice(BaseModel):
    index: int = 0
    message: Dict[str, Any]
    finish_reason: str = "stop"


class OpenAICompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{int(time.time())}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "chatgpt"
    choices: List[OpenAIChoice]
    usage: Dict[str, int] = Field(
        default_factory=lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    )

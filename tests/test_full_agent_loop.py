"""
Full-Fledged Autonomous AI Agent Loop Test.
Tests a multi-turn agent workflow using System Instructions, Dynamic Tool Selection,
Local Python Execution, and Final Answer Synthesis via the official OpenAI SDK.

Usage:
    python tests/test_full_agent_loop.py
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any

# Ensure root workspace directory is in sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import OpenAI
from config.settings import settings

# -------------------------------------------------------------
# 1. MOCK TOOL IMPLEMENTATIONS (Python Runtime)
# -------------------------------------------------------------

def check_server_health(service_name: str) -> Dict[str, Any]:
    """Simulates checking microservice metrics."""
    print(f"   [EXEC] Running Python function: check_server_health('{service_name}')")
    return {
        "service": service_name,
        "status": "online",
        "cpu_usage": "78%",
        "memory_usage": "82%",
        "active_connections": 4120,
        "latency_p99": "240ms"
    }

def check_threat_level(ip_address: str) -> Dict[str, Any]:
    """Simulates querying an IP threat intelligence database."""
    print(f"   [EXEC] Running Python function: check_threat_level('{ip_address}')")
    return {
        "ip": ip_address,
        "reputation_score": 94,
        "verdict": "malicious_botnet",
        "attacks_detected": ["credential_stuffing", "ddos_syn_flood"],
        "action_recommended": "immediate_firewall_drop"
    }

TOOL_REGISTRY = {
    "check_server_health": check_server_health,
    "check_threat_level": check_threat_level
}

# -------------------------------------------------------------
# 2. OPENAI TOOL DEFINITIONS (JSON Schema)
# -------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_server_health",
            "description": "Check real-time health, CPU, memory, and latency metrics for a microservice.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "The name of the service, e.g. auth-gateway, db-primary"
                    }
                },
                "required": ["service_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_threat_level",
            "description": "Query threat intelligence database for reputation and verdict on a suspicious IP address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ip_address": {
                        "type": "string",
                        "description": "The IPv4 or IPv6 address to investigate, e.g. 194.26.29.11"
                    }
                },
                "required": ["ip_address"]
            }
        }
    }
]

# -------------------------------------------------------------
# 3. AUTONOMOUS AGENT LOOP
# -------------------------------------------------------------

def run_agent_test():
    base_url = f"http://{settings.HOST}:{settings.PORT}/v1"
    print("=" * 70)
    print("  FULL-FLEDGED AUTONOMOUS AI AGENT LOOP TEST")
    print(f"  Target Server: {base_url}")
    print("=" * 70)

    client = OpenAI(
        base_url=base_url,
        api_key="not-needed-local"
    )

    system_instruction = (
        "You are CyberSentinel, an elite autonomous cybersecurity & DevOps AI agent. "
        "Your mission is to protect enterprise infrastructure. "
        "MANDATORY PROTOCOL: You must query real tools to gather data before making any decisions. "
        "Format your final answer with professional security headers (INCIDENT SUMMARY, METRICS, ACTION ITEMS)."
    )

    user_query = (
        "We detected an alert on 'auth-gateway'. "
        "First, check the health of 'auth-gateway'. "
        "Then check the threat level of suspicious IP '194.26.29.11'. "
        "Provide your complete analysis."
    )

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_query}
    ]

    print("\n[STEP 0: Agent Initialized]")
    print(f"System Persona: CyberSentinel")
    print(f"User Goal:      {user_query}\n")

    max_turns = 5
    turn = 1

    while turn <= max_turns:
        print(f"\n--- [AGENT ITERATION {turn}] Calling Model ---")
        start_t = time.time()

        response = client.chat.completions.create(
            model="chatgpt",
            messages=messages,
            tools=TOOLS
        )
        duration = round(time.time() - start_t, 2)
        choice = response.choices[0]
        finish_reason = choice.finish_reason

        print(f" * Duration:      {duration}s")
        print(f" * Finish Reason: {finish_reason}")

        # Case A: Agent decides to invoke tools
        if finish_reason == "tool_calls" and choice.message.tool_calls:
            tool_calls = choice.message.tool_calls
            print(f" * Agent Action:  Requested {len(tool_calls)} tool call(s)")

            # Record assistant turn with tool calls
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in tool_calls
                ]
            })

            # Execute each requested tool in local Python environment
            for tc in tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                print(f"   -> Tool:      {fn_name}({fn_args})")

                if fn_name in TOOL_REGISTRY:
                    fn_result = TOOL_REGISTRY[fn_name](**fn_args)
                else:
                    fn_result = {"error": f"Tool '{fn_name}' not registered"}

                # Append tool result to conversation history
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(fn_result)
                })

            turn += 1
            continue

        # Case B: Agent delivers final synthesized answer
        elif finish_reason == "stop":
            final_content = choice.message.content
            print("\n" + "=" * 70)
            print("  AGENT FINAL REPORT DELIVERED:")
            print("=" * 70)
            print(final_content)
            print("=" * 70)
            print(f"\n[+] Full Agent Loop succeeded in {turn} iterations!")
            return True

        else:
            print(f"[!] Unexpected finish_reason: {finish_reason}")
            print(f"    Message: {choice.message.content}")
            break

    print("\n[X] Agent Loop exceeded maximum iterations without completing.")
    return False

if __name__ == "__main__":
    run_agent_test()

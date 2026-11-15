"""Agent definitions.

Each agent is a qwen-agent `Assistant` with its own role (system message) and
tools. To add a new agent, add an entry to AGENTS below and it becomes
available in Discord as `!<name> <message>`.
"""
import os
import re

from qwen_agent.agents import Assistant

MODEL_NAME = os.environ.get("MODEL_NAME", "qwen3.5:4b")
# Ollama runs natively on the Mac (so it can use the M1 GPU via Metal).
# From inside Docker the Mac is reachable at host.docker.internal.
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
# Qwen 3.5 can "think" before answering. Slower but better on hard questions.
ENABLE_THINKING = os.environ.get("ENABLE_THINKING", "false").lower() == "true"

LLM_CFG = {
    "model": MODEL_NAME,
    "model_server": OLLAMA_BASE_URL,
    "api_key": "EMPTY",
    "generate_cfg": {
        # Ollama's OpenAI-compatible API: "none" turns thinking off.
        "extra_body": {"reasoning_effort": "medium" if ENABLE_THINKING else "none"},
    },
}

# name -> (system message, tools). Tools can be qwen-agent built-ins, custom
# tools, or MCP servers, e.g. {"mcpServers": {...}}. Keep tools that run code
# or touch files inside Docker, limited to a dedicated folder.
AGENTS = {
    "default": (
        "Você é um assistente prestativo e direto. Responda no idioma do usuário.",
        [],
    ),
}


def make_agent(name: str = "default") -> Assistant:
    system_message, tools = AGENTS[name]
    return Assistant(llm=LLM_CFG, system_message=system_message, function_list=tools)


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def run_agent(agent: Assistant, messages: list) -> str:
    """Run the agent to completion and return the final answer text (blocking)."""
    final = []
    for response in agent.run(messages=messages):
        final = response
    for msg in reversed(final):
        if msg.get("role") == "assistant" and msg.get("content"):
            content = msg["content"]
            if isinstance(content, list):  # multimodal format
                content = "".join(part.get("text", "") for part in content)
            text = _THINK_RE.sub("", content).strip()
            if text:
                return text
    return "(sem resposta)"


if __name__ == "__main__":
    # Quick terminal test: python3 agent.py
    print(run_agent(make_agent(), [{"role": "user", "content": "Diga olá em uma frase."}]))

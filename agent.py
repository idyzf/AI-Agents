import os
from qwen_agent.agents import Assistant

llm_cfg = {
    "model": os.environ.get("MODEL_NAME", "qwen2.5:7b-instruct"),
    "model_server": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    "api_key": "EMPTY",
}

bot = Assistant(
    llm=llm_cfg,
    function_list=[],  # code_interpreter needs Docker-in-Docker, not set up here
)

if __name__ == "__main__":
    messages = [{"role": "user", "content": "Write and run a script to find prime numbers under 50"}]
    for response in bot.run(messages=messages):
        print(response)
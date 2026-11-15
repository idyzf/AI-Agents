# Only the Discord bot runs here. Ollama runs natively on the Mac so it can use
# the M1 GPU (Docker on macOS has no GPU access).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py discord_bot.py briefing.py google_readonly.py ./

# Run as an unprivileged user inside the container. qwen-agent writes a
# ./workspace folder at startup, so the user needs to own /app.
RUN useradd --create-home bot && chown bot /app
USER bot

ENV OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
ENV MODEL_NAME=qwen3.5:4b

CMD ["python", "discord_bot.py"]

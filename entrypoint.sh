#!/bin/bash
set -e

# Start Ollama's server in the background inside this same container.
ollama serve &
OLLAMA_PID=$!

# Wait until the server is actually ready to accept requests.
echo "Waiting for Ollama to start..."
until curl -sf http://localhost:11434 >/dev/null 2>&1; do
  sleep 1
done
echo "Ollama is up."

# Pull the model on first run. If you docker-commit or use a volume for
# /root/.ollama afterward, this becomes a no-op on later runs.
if ! ollama list | grep -q "$MODEL_NAME"; then
  echo "Pulling $MODEL_NAME (this can take a while on first run)..."
  ollama pull "$MODEL_NAME"
fi

# Hand off to the Discord bot. Runs in the foreground so `docker run`/`docker compose`
# tracks this as the container's main process. Swap back to agent.py if you just
# want the one-shot terminal test instead of the Discord bridge.
python3 discord_bot.py

# Clean shutdown of the background server when the agent exits.
kill $OLLAMA_PID
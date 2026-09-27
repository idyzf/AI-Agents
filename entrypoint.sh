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

# Hand off to the agent. Runs in the foreground so `docker run`/`docker compose`
# tracks this as the container's main process.
python3 agent.py

# Clean shutdown of the background server when the agent exits.
kill $OLLAMA_PID

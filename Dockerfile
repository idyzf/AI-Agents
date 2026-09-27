FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Base deps: curl for the Ollama installer, python for the agent, build tools for
# any tool_list packages that need to compile.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    python3 \
    python3-pip \
    zstd \
    libsndfile1 \
    libfreetype6-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Installs the ollama binary + CLI directly inside this Linux container.
RUN curl -fsSL https://ollama.com/install.sh | sh

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY agent.py discord_bot.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENV OLLAMA_BASE_URL=http://localhost:11434/v1
ENV MODEL_NAME=qwen2.5:7b-instruct

ENTRYPOINT ["./entrypoint.sh"]
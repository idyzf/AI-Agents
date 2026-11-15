#!/bin/bash
# Starts Ollama on the Mac with memory-friendly limits. Ctrl+C stops it and
# frees all of its memory. It does NOT auto-start at login.
export OLLAMA_KEEP_ALIVE=2m          # unload the model 2 min after the last message
export OLLAMA_MAX_LOADED_MODELS=1    # never keep more than one model in RAM
export OLLAMA_NUM_PARALLEL=1         # one answer at a time
export OLLAMA_CONTEXT_LENGTH=4096    # caps memory used by conversation context
export OLLAMA_FLASH_ATTENTION=1      # faster, less memory
export OLLAMA_KV_CACHE_TYPE=q8_0     # halves context memory with no noticeable quality loss
# OLLAMA_HOST stays at its default (127.0.0.1): only this Mac can reach Ollama.
exec ollama serve

#!/bin/sh
set -eu

ollama serve &
server_pid=$!
until ollama list >/dev/null 2>&1; do
  if ! kill -0 "$server_pid" 2>/dev/null; then
    wait "$server_pid"
  fi
  sleep 2
done
ollama pull "${OLLAMA_MODEL:-llama3:8b-instruct-q4_K_M}"
wait "$server_pid"

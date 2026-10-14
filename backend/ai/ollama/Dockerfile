FROM ollama/ollama:latest

ENV OLLAMA_HOST=0.0.0.0:11434
ENV OLLAMA_MODEL=llama3:8b-instruct-q4_K_M
COPY entrypoint.sh /usr/local/bin/naviora-ollama-entrypoint
RUN chmod +x /usr/local/bin/naviora-ollama-entrypoint
EXPOSE 11434
ENTRYPOINT ["/usr/local/bin/naviora-ollama-entrypoint"]

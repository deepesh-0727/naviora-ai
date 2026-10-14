FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04
ENV DEBIAN_FRONTEND=noninteractive
ENV WHISPER_MODEL=small
ENV WHISPER_DEVICE=cuda
WORKDIR /service
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt
COPY service.py .
EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8000"]

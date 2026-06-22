FROM python:3.11-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl && \
    rm -rf /var/lib/apt/lists/*
COPY services/chatbot-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/chatbot-api/ .
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["python", "run.py"]

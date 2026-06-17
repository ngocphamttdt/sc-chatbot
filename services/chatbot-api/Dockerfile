FROM node:20-alpine AS frontend
WORKDIR /build
COPY services/web-admin/package*.json ./
RUN npm ci
COPY services/web-admin/ .
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM python:3.11-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl && \
    rm -rf /var/lib/apt/lists/*
COPY services/chatbot-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/chatbot-api/ .
COPY --from=frontend /build/dist /app/static/web-admin
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["python", "run.py"]

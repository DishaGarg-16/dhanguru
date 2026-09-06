# Multi-stage build: React Frontend + FastAPI Backend in a single lightweight container
# Stage 1: Build React/Vite frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /build

# Copy dependency manifests for caching
COPY frontend/package*.json ./
RUN npm install

# Copy frontend source and build production bundle
COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python backend
FROM python:3.12-slim
WORKDIR /app

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Kolkata

# Install curl for health checks and tzdata for Indian Standard Time (IST)
RUN apt-get update && apt-get install -y --no-install-recommends curl tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy backend source code
COPY backend/ ./backend/

# Copy compiled frontend assets from Stage 1
COPY --from=frontend-builder /build/dist ./frontend/dist

EXPOSE 8000

# Container health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start FastAPI via Uvicorn respecting dynamic Railway PORT
CMD ["sh", "-c", "exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

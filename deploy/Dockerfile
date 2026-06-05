# --- Stage 1: Frontend Build ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: C Core Build ---
FROM python:3.11-slim AS c-builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*
COPY c_core/ ./c_core/
WORKDIR /app/c_core
RUN chmod +x compile.sh && ./compile.sh

# --- Stage 3: Final Runtime ---
FROM python:3.11-slim
WORKDIR /app

# Install runtime dependencies for C libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled C libraries
COPY --from=c-builder /app/lib /app/lib

# Copy frontend build artifacts
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend /app/backend
COPY .env.example /app/.env

WORKDIR /app/backend

# Create persistent storage directories (relative to /app)
RUN mkdir -p ../storage/thumbnails ../logs ../storage/temp

# Environment variables
ENV PYTHONPATH=/app/backend
ENV LOG_LEVEL=INFO
ENV FRONTEND_DIST_DIR=/app/frontend/dist

# Expose port
EXPOSE 8000

# Use exec form for proper signal handling (PID 1)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

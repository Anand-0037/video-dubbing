# Multi-stage build for Worker
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install shared package first
COPY packages/shared /app/packages/shared
RUN pip install --user --no-cache-dir -e /app/packages/shared

# Install Python dependencies
COPY worker/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install FFmpeg and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/packages/shared /app/packages/shared
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app/packages/shared:$PYTHONPATH

# Copy worker code
COPY worker/ /app/worker/

# Create temp directory for processing
RUN mkdir -p /tmp/dubwizard

# Run the worker
CMD ["python", "-m", "worker.worker"]

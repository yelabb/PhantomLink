# PhantomLink Docker Image
# Multi-stage build for optimal image size

FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libhdf5-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libhdf5-103 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY main.py ./
COPY data/ ./data/
COPY docker-entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Create non-root user for security
RUN useradd -m -u 1000 phantomlink && \
    chown -R phantomlink:phantomlink /app

USER phantomlink

# Expose ports
# 8000: HTTP/WebSocket server
# 8001-8010: Additional ports for multi-session or LSL
EXPOSE 8000

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PHANTOM_HOST=0.0.0.0 \
    PHANTOM_PORT=8000

# Health check for WebSocket/HTTP server
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Use custom entrypoint for dataset handling
ENTRYPOINT ["./docker-entrypoint.sh"]

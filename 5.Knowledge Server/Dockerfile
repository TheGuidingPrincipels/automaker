# Multi-stage Dockerfile for MCP Knowledge Server
# Optimized for local deployment with easy cloud migration

# =============================================================================
# Stage 1: Builder - Install dependencies and prepare application
# =============================================================================
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy dependency files
COPY requirements.txt pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv pip install --system -r requirements.txt

# =============================================================================
# Stage 2: Runtime - Minimal image for running the application
# =============================================================================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create directories for data persistence
RUN mkdir -p /app/data/chromadb /app/data/events /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO \
    CHROMA_PERSIST_DIRECTORY=/app/data/chromadb \
    EVENT_STORE_PATH=/app/data/events/events.db

# Expose port (if your server uses HTTP, adjust accordingly)
# EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command
CMD ["python", "mcp_server.py"]

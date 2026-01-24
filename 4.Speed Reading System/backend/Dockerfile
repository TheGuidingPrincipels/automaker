FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . .

# Install Python dependencies (from pyproject.toml)
RUN pip install --no-cache-dir .

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

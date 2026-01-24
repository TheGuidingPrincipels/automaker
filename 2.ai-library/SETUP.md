# AI-Library Setup Guide

This guide covers setting up the Python development environment for the AI-Library module.

## Prerequisites

- **Python 3.11+** (recommended: 3.12)
- **uv** - Fast Python package installer and resolver

### Installing uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv

# Or with pip
pip install uv
```

## Quick Start

```bash
# Navigate to the AI-Library directory
cd 2.ai-library

# Create virtual environment and install dependencies (including dev/test)
uv venv
uv sync --all-extras

# Activate the virtual environment
source .venv/bin/activate
```

**Blessed setup command:**

`cd 2.ai-library && uv venv && uv sync --all-extras`

## Environment Setup

### 1. Create Virtual Environment

```bash
cd 2.ai-library
uv venv
```

This creates a `.venv/` directory with an isolated Python environment.

### 2. Install Dependencies

```bash
# Install all dependencies from pyproject.toml
uv sync

# Install with dev dependencies explicitly (recommended for tests)
uv sync --all-extras
```

### 3. Activate Environment

```bash
# macOS/Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat
```

### 4. Verify Installation

```bash
# Check Python version
python --version

# Run tests to verify setup
python3 -m pytest -q
```

## Configuration

### Environment Variables

Create a `.env` file in the `ai-library/` directory (if needed):

```bash
# API Keys (if using external services)
OPENAI_API_KEY=your-key-here
MISTRAL_API_KEY=your-key-here

# Optional: Anthropic for Claude SDK
ANTHROPIC_API_KEY=your-key-here
```

### Settings

Application settings are in `configs/settings.yaml`. Review and adjust as needed:

```yaml
# configs/settings.yaml
library_path: ./library
sessions_path: ./sessions
```

## Running the Application

### Start the API Server

```bash
# From 2.ai-library directory with venv activated
python run_api.py

# Or with uvicorn directly
uvicorn src.api.main:app --reload --port 8001
```

### Run Tests

```bash
# Run all tests (blessed command)
python3 -m pytest -q

# Run with verbose output
python3 -m pytest -v

# Run specific test file
python3 -m pytest tests/test_extraction.py

# Run with coverage
python3 -m pytest --cov=src
```

## Development Workflow

### Adding Dependencies

```bash
# Add a runtime dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Update all dependencies
uv sync --upgrade
```

### Code Quality

```bash
# Format code with ruff
ruff format .

# Lint code
ruff check .

# Type checking (if mypy is installed)
mypy src/
```

## Project Structure

```
2.ai-library/
├── src/                    # Source code
│   ├── api/               # REST API (FastAPI)
│   ├── extraction/        # Content parsing & checksums
│   ├── models/            # Pydantic data models
│   ├── query/             # Query engine
│   ├── session/           # Session management
│   ├── vector/            # Vector embeddings & search
│   └── ...
├── tests/                  # Test suite
│   └── fixtures/          # Test data
├── configs/               # Configuration files
├── library/               # Knowledge library storage
├── sessions/              # Session data
├── Docs/                  # Documentation
├── pyproject.toml         # Project config & dependencies
├── uv.lock               # Locked dependencies
└── run_api.py            # API entry point
```

## Troubleshooting

### Virtual Environment Issues

```bash
# Remove and recreate venv
rm -rf .venv
uv venv
uv sync
```

### Dependency Conflicts

```bash
# Clear cache and reinstall
uv cache clean
uv sync --refresh
```

### Import Errors

Ensure you're running from the `ai-library/` directory with the virtual environment activated:

```bash
cd 2.ai-library
source .venv/bin/activate
python -c "import src; print('OK')"
```

## Integration with Automaker

The AI-Library is a Python module within the Automaker monorepo. It operates independently but can be integrated with the main TypeScript application through:

1. **REST API** - Run as a service on a configurable port
2. **CLI** - Direct Python script execution
3. **SDK** - Import and use from other Python scripts

The TypeScript apps can communicate with ai-library via HTTP requests to the FastAPI server.

### Frontend Configuration

To enable Knowledge Library features in the Automaker UI, configure the following environment variable:

```bash
# In the root .env file (or apps/ui/.env)
VITE_KNOWLEDGE_LIBRARY_API=http://localhost:8001
```

This tells the frontend where to find the AI-Library API server. The default value is `http://localhost:8001`.

**Full setup workflow:**

1. Start the AI-Library backend:

   ```bash
   cd 2.ai-library
   source .venv/bin/activate
   python run_api.py
   ```

2. Set the environment variable in your `.env`:

   ```bash
   VITE_KNOWLEDGE_LIBRARY_API=http://localhost:8001
   ```

3. Start the Automaker UI (it will now connect to the Knowledge Library API)

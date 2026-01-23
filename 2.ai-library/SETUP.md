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
# Navigate to ai-library directory
cd /path/to/automaker/ai-library

# Create virtual environment and install dependencies
uv venv
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

## Environment Setup

### 1. Create Virtual Environment

```bash
cd ai-library
uv venv
```

This creates a `.venv/` directory with an isolated Python environment.

### 2. Install Dependencies

```bash
# Install all dependencies from pyproject.toml
uv sync

# Or install with dev dependencies explicitly
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
pytest
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
# From ai-library directory with venv activated
python run_api.py

# Or with uvicorn directly
uvicorn src.api.main:app --reload --port 8000
```

### Run Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_extraction.py

# Run with coverage
pytest --cov=src
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
ai-library/
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
cd ai-library
source .venv/bin/activate
python -c "import src; print('OK')"
```

## Integration with Automaker

The AI-Library is a Python module within the Automaker monorepo. It operates independently but can be integrated with the main TypeScript application through:

1. **REST API** - Run as a service on a configurable port
2. **CLI** - Direct Python script execution
3. **SDK** - Import and use from other Python scripts

The TypeScript apps can communicate with ai-library via HTTP requests to the FastAPI server.

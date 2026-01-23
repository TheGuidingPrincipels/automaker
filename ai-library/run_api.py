#!/usr/bin/env python3
"""Run the Knowledge Library API server."""

import argparse
import sys
import uvicorn
import anyio

from src.config import load_config


def main():
    """Run the API server."""
    parser = argparse.ArgumentParser(description="Run the Knowledge Library API")
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind to (default: from config)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to (default: from config)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )

    args = parser.parse_args()

    # Load config for defaults
    try:
        config = anyio.run(load_config)
    except Exception as e:
        print(f"Failed to load config: {e}", file=sys.stderr)
        raise SystemExit(1) from e

    host = args.host or config.api.host
    port = args.port or config.api.port

    print(f"Starting Knowledge Library API on http://{host}:{port}")
    print(f"  - Swagger UI: http://{host}:{port}/docs")
    print(f"  - ReDoc: http://{host}:{port}/redoc")
    print(f"  - Health: http://{host}:{port}/health")

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=args.reload,
        log_level="debug" if args.debug else "info",
    )


if __name__ == "__main__":
    main()

# src/utils/async_helpers.py
import asyncio
from typing import TypeVar, Coroutine, Any

T = TypeVar("T")


def _run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run an async coroutine synchronously.
    
    Safe to use whether or not there is an existing running loop,
    though it primarily exists to bridge sync methods to async implementation
    where the caller is definitely synchronous (blocking).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    
    raise RuntimeError(
        "Cannot run synchronous blocking logic inside an active event loop. "
        "Use the `await async_method()` version instead."
    )

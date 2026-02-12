"""
Lazy async initialization and explicit init/close for Tortoise ORM.

Provides ``init()`` and ``close()`` coroutines that manage the Tortoise
ORM lifecycle, including double-check locking for thread-safe lazy init.
"""

from __future__ import annotations

import asyncio
import logging

from tortoise import Tortoise

from django_tortoise.db_config import build_tortoise_config
from django_tortoise.exceptions import ConnectionError

logger = logging.getLogger("django_tortoise")

_initialized: bool = False
_init_lock: asyncio.Lock | None = None


async def _ensure_lock() -> asyncio.Lock:
    """Get or create the init lock (lazily, to avoid event loop binding at import time)."""
    global _init_lock
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    return _init_lock


async def ensure_initialized() -> None:
    """
    Ensure Tortoise ORM is initialized. Called automatically before queries.

    Uses double-check locking with ``asyncio.Lock`` for safety.
    """
    global _initialized
    if _initialized:
        return

    lock = await _ensure_lock()
    async with lock:
        if _initialized:
            return  # Another coroutine already initialized
        await init()


async def init() -> None:
    """
    Explicitly initialize Tortoise ORM connections using Django's DATABASES config.

    Idempotent: calling multiple times is a no-op after the first success.
    Can be called from ASGI lifespan handler for pre-warming connections.
    """
    global _initialized
    if _initialized:
        logger.debug("Tortoise already initialized, skipping.")
        return

    logger.info("Initializing Tortoise ORM connections...")

    try:
        config = build_tortoise_config()
        await Tortoise.init(config=config)
        _initialized = True
        logger.info("Tortoise ORM initialized successfully.")
    except Exception as exc:
        raise ConnectionError(f"Failed to initialize Tortoise ORM: {exc}") from exc


async def close() -> None:
    """
    Close all Tortoise ORM connections.

    Call this during ASGI shutdown or when cleaning up.
    """
    global _initialized
    if not _initialized:
        return

    logger.info("Closing Tortoise ORM connections...")
    try:
        await Tortoise.close_connections()
    except RuntimeError:
        # Handle case where Tortoise context is no longer active
        # (e.g., in test teardown scenarios)
        logger.debug("Tortoise context already closed.")
    _initialized = False
    logger.info("Tortoise ORM connections closed.")


def is_initialized() -> bool:
    """Check if Tortoise ORM has been initialized."""
    return _initialized


def _reset_for_testing() -> None:
    """Reset initialization state. For testing only."""
    global _initialized, _init_lock
    _initialized = False
    _init_lock = None

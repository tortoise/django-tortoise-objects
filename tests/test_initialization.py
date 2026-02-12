"""
Tests for django_tortoise.initialization -- Lazy async init and close.

Verifies init/close lifecycle, idempotency, concurrent safety, and state
tracking via ``is_initialized()``.
"""

import asyncio
import contextlib

import pytest

from django_tortoise.initialization import (
    _reset_for_testing,
    close,
    ensure_initialized,
    init,
    is_initialized,
)


@pytest.fixture(autouse=True)
async def reset_init():
    """Reset init state before and after each test."""
    _reset_for_testing()
    yield
    # Clean up after test
    if is_initialized():
        with contextlib.suppress(Exception):
            await close()
    _reset_for_testing()


@pytest.mark.asyncio
async def test_init_initializes():
    """init() should set initialized state to True."""
    assert not is_initialized()
    await init()
    assert is_initialized()
    await close()


@pytest.mark.asyncio
async def test_init_idempotent():
    """Calling init() twice is safe."""
    await init()
    assert is_initialized()
    await init()  # Should not raise
    assert is_initialized()
    await close()


@pytest.mark.asyncio
async def test_close_when_not_initialized():
    """Closing when not initialized is a no-op."""
    assert not is_initialized()
    await close()  # Should not raise
    assert not is_initialized()


@pytest.mark.asyncio
async def test_ensure_initialized():
    """ensure_initialized() triggers init on first call."""
    assert not is_initialized()
    await ensure_initialized()
    assert is_initialized()
    await close()


@pytest.mark.asyncio
async def test_ensure_initialized_idempotent():
    """Repeated calls to ensure_initialized() are no-ops after first."""
    await ensure_initialized()
    await ensure_initialized()
    assert is_initialized()
    await close()


@pytest.mark.asyncio
async def test_concurrent_init():
    """Multiple concurrent ensure_initialized() calls should be safe."""
    await asyncio.gather(
        ensure_initialized(),
        ensure_initialized(),
        ensure_initialized(),
    )
    assert is_initialized()
    await close()


@pytest.mark.asyncio
async def test_init_close_cycle():
    """Can init, close, and re-init."""
    await init()
    assert is_initialized()
    await close()
    assert not is_initialized()
    await init()
    assert is_initialized()
    await close()
    assert not is_initialized()


@pytest.mark.asyncio
async def test_close_resets_state():
    """close() sets initialized to False."""
    await init()
    assert is_initialized()
    await close()
    assert not is_initialized()


def test_reset_for_testing():
    """_reset_for_testing clears state."""
    # We cannot set _initialized directly, but _reset works
    _reset_for_testing()
    assert not is_initialized()

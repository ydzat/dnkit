"""
Test configuration for MCP Toolkit.
"""

import asyncio
from pathlib import Path

import pytest


# Test fixtures
@pytest.fixture
def test_config_path():
    """Return path to test configuration."""
    return Path(__file__).parent / "fixtures" / "test_config.yaml"


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Async test support
pytest_plugins = ["pytest_asyncio"]

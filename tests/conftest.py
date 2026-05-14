"""pytest configuration and shared fixtures."""
import pytest
import os
import sys

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    """Set minimal env vars so Settings() doesn't fail during tests."""
    monkeypatch.setenv("NAUKRI_EMAIL", "test@example.com")
    monkeypatch.setenv("NAUKRI_PASSWORD", "testpassword")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("MODEL", "gpt-4o-mini")

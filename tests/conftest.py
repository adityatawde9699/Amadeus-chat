"""Shared fixtures.  Everything is isolated to ``tmp_path`` so tests never
touch the real ``~/.amadeus`` directory or the network."""
from __future__ import annotations

import pytest

from amadeus.core.config import ensure_amadeus_home, load_config


@pytest.fixture()
def home(tmp_path):
    """An isolated Amadeus home directory."""
    return ensure_amadeus_home(tmp_path / ".amadeus")


@pytest.fixture()
def cfg(home):
    """A Config rooted at the isolated home."""
    return load_config(home)

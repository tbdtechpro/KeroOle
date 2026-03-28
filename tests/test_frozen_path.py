"""Tests for kerole.py frozen-exe PATH resolution."""
import importlib
import os
import sys
import pytest


def test_frozen_path_uses_executable_directory(monkeypatch, tmp_path):
    """When sys.frozen is True, PATH must be the directory containing the exe."""
    fake_exe = str(tmp_path / "KeroOle.exe")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", fake_exe)

    import kerole
    importlib.reload(kerole)

    assert kerole.PATH == str(tmp_path)
    assert kerole.COOKIES_FILE == str(tmp_path / "cookies.json")


def test_unfrozen_path_uses_source_directory():
    """When not frozen, PATH must be the directory containing kerole.py."""
    import kerole
    importlib.reload(kerole)

    expected = os.path.dirname(os.path.realpath(kerole.__file__))
    assert kerole.PATH == expected

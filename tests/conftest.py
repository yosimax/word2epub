"""Shared fixtures for the yaml2epub regression test suite."""
import importlib.util
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DIR = os.path.join(REPO_ROOT, "sample_yaml")
META_PATH = os.path.join(SAMPLE_DIR, "metadata.yaml")


def _load_module(name: str, path: str) -> type:
    """Load a top-level module from an explicit file path.

    Loading by path avoids ambiguity with the empty ``yaml2epub/`` directory
    that sits next to ``yaml2epub.py`` in the repo root.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"cannot load module from {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def module() -> type:
    return _load_module("yaml2epub", os.path.join(REPO_ROOT, "yaml2epub.py"))


@pytest.fixture(scope="session")
def sample_dir() -> str:
    return SAMPLE_DIR


@pytest.fixture(scope="session")
def meta_path() -> str:
    return META_PATH


@pytest.fixture(scope="module")
def module_main(module):
    return module.main

"""Shared fixtures for the yaml2epub regression test suite."""

import importlib.util
import os
import sys
from types import ModuleType

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DIR = os.path.join(REPO_ROOT, "sample_yaml")
META_PATH = os.path.join(SAMPLE_DIR, "metadata.yaml")

# The entry script imports the real ``yaml2epub`` package (``from
# yaml2epub.pipeline import main``), so the repo root must be importable
# without installing the project.
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _load_module(name: str, path: str) -> ModuleType:
    """Load a module from an explicit file path under the given name.

    Loading by path is used to import the ``yaml2epub.py`` entry script without
    letting it shadow the ``yaml2epub/`` package that lives next to it.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"cannot load module from {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def module() -> ModuleType:
    # Loaded under an alias so it does not clobber the ``yaml2epub`` package
    # that the entry script imports from.
    return _load_module("yaml2epub_cli", os.path.join(REPO_ROOT, "yaml2epub.py"))


@pytest.fixture(scope="session")
def sample_dir() -> str:
    return SAMPLE_DIR


@pytest.fixture(scope="session")
def meta_path() -> str:
    return META_PATH


@pytest.fixture(scope="module")
def module_main(module):
    return module.main

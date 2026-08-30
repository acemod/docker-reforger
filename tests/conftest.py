from pathlib import Path

import pytest

from src.launch_config import load_json_file

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def base_config():
    return load_json_file(REPO_ROOT / "src" / "docker_default.json")

"""End-to-end prune test using the sample mod JSON.

Run with `pytest tests/test_prune_integration.py` (no Docker, no SteamCMD, no
server boot). It exercises the same GAME_MODS_JSON_FILE_PATH path that
launch.py uses, plus the pruning behavior.
"""

import json
from pathlib import Path

from src.launch_config import build_config, prune_mods

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE_MODS = FIXTURES / "sample_mods.json"


def sample_mod_ids():
    return [mod["modId"] for mod in json.loads(SAMPLE_MODS.read_text())]


def _write_config(tmp_path, mod_ids):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {"game": {"name": "Test", "mods": [{"modId": mid} for mid in mod_ids]}}
        )
    )
    return config_path


def _write_mod(workshop, mod_id, name=None, dependencies=None):
    mod_dir = workshop / mod_id
    mod_dir.mkdir()
    server_data = {
        "id": mod_id,
        "name": name or f"Mod {mod_id}",
        "revision": {
            "version": "1.0.0",
            "dependencies": dependencies or [],
            "downloaded": True,
        },
    }
    (mod_dir / "ServerData.json").write_text(json.dumps(server_data))
    return mod_dir


def test_sample_mods_json_loads():
    ids = sample_mod_ids()
    assert len(ids) == 19
    assert all(len(mod_id) == 16 for mod_id in ids)


def test_sample_mods_load_through_build_config(base_config):
    config = build_config(
        {"GAME_MODS_JSON_FILE_PATH": str(SAMPLE_MODS)},
        base_config,
    )
    loaded_ids = [mod["modId"] for mod in config["game"]["mods"]]
    assert loaded_ids == sample_mod_ids()
    ace_ballistics = next(
        mod for mod in config["game"]["mods"] if mod["modId"] == "68F77A54920B80AF"
    )
    assert ace_ballistics["version"] == "1.5.34"


def test_prune_keeps_configured_mods_and_removes_stale(tmp_path):
    ids = sample_mod_ids()
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    configured = ids[:3]
    for mod_id in configured:
        _write_mod(workshop, mod_id)
    stale = _write_mod(workshop, "AAAAAAAAAAAAA000")
    unrelated = workshop / "notes"
    unrelated.mkdir()
    (unrelated / "content.txt").write_text("keep")
    config = _write_config(tmp_path, configured)

    pruned = prune_mods(config, workshop)
    assert pruned == [stale]
    for mod_id in configured:
        assert (workshop / mod_id).exists()
    assert not stale.exists()
    assert unrelated.exists()


def test_prune_no_op_when_all_installed_mods_are_configured(tmp_path):
    ids = sample_mod_ids()
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    for mod_id in ids:
        _write_mod(workshop, mod_id)
    config = _write_config(tmp_path, ids)

    assert not prune_mods(config, workshop)
    for mod_id in ids:
        assert (workshop / mod_id).exists()

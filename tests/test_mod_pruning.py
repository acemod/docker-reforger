import json
import os
import sys

import pytest

from src import launch_config
from src.launch_config import prune_mods

MOD_A = "1111111111111111"
MOD_B = "2222222222222222"
MOD_C = "3333333333333333"
MOD_D = "4444444444444444"
MOD_E = "5555555555555555"


def write_config(tmp_path, mod_ids):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"game": {"mods": [{"modId": mod_id} for mod_id in mod_ids]}})
    )
    return path


def write_mod(workshop, mod_id, dependencies=None, encoding="utf-8"):
    mod_dir = workshop / mod_id
    mod_dir.mkdir()
    server_data = {
        "id": mod_id,
        "name": f"Mod {mod_id}",
        "revision": {
            "version": "1.0.0",
            "dependencies": dependencies or [],
            "downloaded": True,
        },
    }
    (mod_dir / "ServerData.json").write_text(json.dumps(server_data), encoding=encoding)
    return mod_dir


def patch_revision(mod_dir, **changes):
    path = mod_dir / "ServerData.json"
    server_data = json.loads(path.read_text())
    server_data["revision"].update(changes)
    path.write_text(json.dumps(server_data))


def test_prunes_only_unreferenced_mods(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    configured = write_mod(workshop, MOD_A)
    stale = write_mod(workshop, MOD_B)
    nested = stale / "data"
    nested.mkdir()
    (nested / "content.bin").write_bytes(b"content")
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("keep")
    (stale / "outside-link").symlink_to(outside_file)
    config = write_config(tmp_path, [MOD_A])

    assert prune_mods(config, workshop) == [stale]
    assert configured.exists()
    assert not stale.exists()
    assert outside_file.exists()


def test_preserves_transitive_dependencies(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    root = write_mod(workshop, MOD_A, [{"id": MOD_B}])
    dependency = write_mod(workshop, MOD_B, [MOD_C])
    transitive_dependency = write_mod(workshop, MOD_C)
    stale = write_mod(workshop, MOD_D)
    config = write_config(tmp_path, [MOD_A])

    assert prune_mods(config, workshop) == [stale]
    assert root.exists()
    assert dependency.exists()
    assert transitive_dependency.exists()


def test_skips_directories_without_valid_server_data(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    invalid = workshop / MOD_A
    invalid.mkdir()
    (invalid / "ServerData.json").write_text("not json")
    unrelated = workshop / "notes"
    unrelated.mkdir()
    config = write_config(tmp_path, [])

    assert not prune_mods(config, workshop)
    assert invalid.exists()
    assert unrelated.exists()


def test_skips_mod_with_non_string_metadata_id(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    invalid = write_mod(workshop, MOD_A)
    server_data_path = invalid / "ServerData.json"
    server_data = json.loads(server_data_path.read_text())
    server_data["id"] = 123
    server_data_path.write_text(json.dumps(server_data))
    config = write_config(tmp_path, [])

    assert not prune_mods(config, workshop)
    assert invalid.exists()


def test_skips_symlinked_server_data(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    invalid = write_mod(workshop, MOD_A)
    server_data_path = invalid / "ServerData.json"
    server_data_path.unlink()
    outside_metadata = tmp_path / "outside.json"
    outside_metadata.write_text("{}")
    server_data_path.symlink_to(outside_metadata)
    config = write_config(tmp_path, [])

    assert not prune_mods(config, workshop)
    assert invalid.exists()
    assert outside_metadata.exists()


def test_skips_oversized_server_data(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    invalid = workshop / MOD_A
    invalid.mkdir()
    (invalid / "ServerData.json").write_bytes(
        b"x" * (launch_config.MAX_SERVER_DATA_SIZE + 1)
    )
    config = write_config(tmp_path, [])

    assert not prune_mods(config, workshop)
    assert invalid.exists()


def test_invalid_required_mod_aborts_before_pruning(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    invalid = workshop / MOD_A
    invalid.mkdir()
    (invalid / "ServerData.json").write_text("not json")
    stale = write_mod(workshop, MOD_B)
    config = write_config(tmp_path, [MOD_A])

    with pytest.raises(ValueError, match="required mod .* is invalid"):
        prune_mods(config, workshop)
    assert invalid.exists()
    assert stale.exists()


def test_invalid_dependency_aborts_before_pruning(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    write_mod(workshop, MOD_A, [{"id": MOD_B}])
    invalid_dependency = workshop / MOD_B
    invalid_dependency.mkdir()
    stale = write_mod(workshop, MOD_C)
    config = write_config(tmp_path, [MOD_A])

    with pytest.raises(ValueError, match="required mod .* is invalid"):
        prune_mods(config, workshop)
    assert invalid_dependency.exists()
    assert stale.exists()


@pytest.mark.parametrize("invalid_mod_id", ["invalid", 123])
def test_invalid_config_aborts_before_pruning(tmp_path, invalid_mod_id):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    stale = write_mod(workshop, MOD_A)
    config = write_config(tmp_path, [invalid_mod_id])

    with pytest.raises(ValueError, match="Invalid mod ID"):
        prune_mods(config, workshop)
    assert stale.exists()


def test_custom_config_without_mods_prunes_all(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    stale = write_mod(workshop, MOD_A)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"game": {"name": "Vanilla"}}))

    assert prune_mods(config, workshop) == [stale]
    assert not stale.exists()


def test_refuses_mod_directories_containing_mounts(tmp_path, monkeypatch):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    stale = write_mod(workshop, MOD_A)
    nested_mount = stale / "mounted"
    nested_mount.mkdir()
    sentinel = nested_mount / "sentinel"
    sentinel.write_text("keep")
    config = write_config(tmp_path, [])
    monkeypatch.setattr(launch_config, "mounted_paths", lambda: {nested_mount})

    with pytest.raises(ValueError, match="mounted content"):
        prune_mods(config, workshop)
    assert sentinel.exists()


def test_workshop_symlink_retarget_does_not_change_prune_root(tmp_path, monkeypatch):
    first_workshop = tmp_path / "first"
    first_workshop.mkdir()
    stale = write_mod(first_workshop, MOD_A)
    second_workshop = tmp_path / "second"
    second_workshop.mkdir()
    protected = write_mod(second_workshop, MOD_A)
    workshop_link = tmp_path / "workshop"
    workshop_link.symlink_to(first_workshop, target_is_directory=True)
    config = write_config(tmp_path, [])
    mount_paths = launch_config.mounted_paths()

    def retarget_workshop():
        workshop_link.unlink()
        workshop_link.symlink_to(second_workshop, target_is_directory=True)
        return mount_paths

    monkeypatch.setattr(launch_config, "mounted_paths", retarget_workshop)

    assert prune_mods(config, workshop_link) == [stale]
    assert not stale.exists()
    assert protected.exists()


def test_does_not_follow_symlinked_mod_directories(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_mod = write_mod(outside, MOD_A)
    (workshop / MOD_A).symlink_to(outside_mod, target_is_directory=True)
    config = write_config(tmp_path, [])

    assert not prune_mods(config, workshop)
    assert outside_mod.exists()


def test_configured_symlinked_mod_aborts_before_pruning(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_mod = write_mod(outside, MOD_A)
    (workshop / MOD_A).symlink_to(outside_mod, target_is_directory=True)
    stale = write_mod(workshop, MOD_B)
    config = write_config(tmp_path, [MOD_A])

    with pytest.raises(ValueError, match="required mod .* is invalid"):
        prune_mods(config, workshop)
    assert outside_mod.exists()
    assert stale.exists()


def test_candidate_replacement_is_not_recursively_deleted(tmp_path, monkeypatch):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    stale = write_mod(workshop, MOD_A)
    moved = workshop / "moved"
    replacement_sentinel = stale / "sentinel"
    config = write_config(tmp_path, [])
    stage_candidates = launch_config.stage_prune_candidates

    def replace_candidate(workshop_fd, expected_mount_id, candidates):
        stale.rename(moved)
        stale.mkdir()
        replacement_sentinel.write_text("keep")
        return stage_candidates(workshop_fd, expected_mount_id, candidates)

    monkeypatch.setattr(launch_config, "stage_prune_candidates", replace_candidate)

    with pytest.raises(OSError, match="roll back staged mods"):
        prune_mods(config, workshop)
    quarantine = next(
        path
        for path in workshop.iterdir()
        if path.name.startswith(launch_config.PRUNE_QUARANTINE_PREFIX)
    )
    assert (quarantine / MOD_A / "sentinel").exists()
    assert moved.exists()
    with pytest.raises(ValueError, match="Invalid quarantined mod entry"):
        prune_mods(config, workshop)


def test_staging_failure_rolls_back_all_candidates(tmp_path, monkeypatch):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    first = write_mod(workshop, MOD_A)
    second = write_mod(workshop, MOD_B)
    config = write_config(tmp_path, [])
    rename = launch_config.os.rename
    rename_calls = 0

    def fail_second_rename(*args, **kwargs):
        nonlocal rename_calls
        rename_calls += 1
        if rename_calls == 2:
            raise OSError("staging failed")
        return rename(*args, **kwargs)

    monkeypatch.setattr(launch_config.os, "rename", fail_second_rename)

    with pytest.raises(OSError, match="staging failed"):
        prune_mods(config, workshop)
    assert first.exists()
    assert second.exists()
    assert not any(
        path.name.startswith(launch_config.PRUNE_QUARANTINE_PREFIX)
        for path in workshop.iterdir()
    )


def test_deletion_failure_is_retried_from_quarantine(tmp_path, monkeypatch):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    first = write_mod(workshop, MOD_A)
    second = write_mod(workshop, MOD_B)
    config = write_config(tmp_path, [])
    remove_tree = launch_config.remove_directory_tree
    remove_calls = 0

    def fail_second_removal(*args, **kwargs):
        nonlocal remove_calls
        remove_calls += 1
        if remove_calls == 2:
            raise OSError("deletion failed")
        return remove_tree(*args, **kwargs)

    monkeypatch.setattr(launch_config, "remove_directory_tree", fail_second_removal)

    with pytest.raises(OSError, match="deletion failed"):
        prune_mods(config, workshop)
    assert not first.exists()
    assert not second.exists()
    assert any(
        path.name.startswith(launch_config.PRUNE_QUARANTINE_PREFIX)
        for path in workshop.iterdir()
    )

    monkeypatch.setattr(launch_config, "remove_directory_tree", remove_tree)
    assert not prune_mods(config, workshop)
    assert not any(
        path.name.startswith(launch_config.PRUNE_QUARANTINE_PREFIX)
        for path in workshop.iterdir()
    )


def test_interrupted_quarantine_is_recovered(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    stale = write_mod(workshop, MOD_A)
    config = write_config(tmp_path, [])
    workshop_fd = os.open(workshop, launch_config.WORKSHOP_OPEN_FLAGS)
    try:
        mod_fd = os.open(MOD_A, launch_config.DIRECTORY_OPEN_FLAGS, dir_fd=workshop_fd)
        try:
            candidate = launch_config.load_installed_mod(MOD_A, mod_fd, stale)
        finally:
            os.close(mod_fd)
        quarantine_name, quarantine_fd = launch_config.stage_prune_candidates(
            workshop_fd,
            launch_config.fd_mount_id(workshop_fd),
            [candidate],
        )
        quarantined_mod_fd = os.open(
            MOD_A,
            launch_config.DIRECTORY_OPEN_FLAGS,
            dir_fd=quarantine_fd,
        )
        try:
            os.unlink(launch_config.SERVER_DATA_FILE, dir_fd=quarantined_mod_fd)
        finally:
            os.close(quarantined_mod_fd)
        os.close(quarantine_fd)
    finally:
        os.close(workshop_fd)

    assert not stale.exists()
    assert (workshop / quarantine_name).exists()
    assert not prune_mods(config, workshop)
    assert not stale.exists()
    assert not (workshop / quarantine_name).exists()


def test_workshop_descriptor_closes_when_fd_path_fails(tmp_path, monkeypatch):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    config = write_config(tmp_path, [])
    open_fd_count = len(os.listdir("/proc/self/fd"))

    def fail_fd_path(_fd):
        raise OSError("fd path failed")

    monkeypatch.setattr(launch_config, "fd_path", fail_fd_path)

    with pytest.raises(OSError, match="fd path failed"):
        prune_mods(config, workshop)
    assert len(os.listdir("/proc/self/fd")) == open_fd_count


def test_concurrent_pruner_is_rejected(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    config = write_config(tmp_path, [])
    workshop_fd = os.open(workshop, launch_config.WORKSHOP_OPEN_FLAGS)
    launch_config.fcntl.flock(workshop_fd, launch_config.fcntl.LOCK_EX)
    try:
        with pytest.raises(BlockingIOError):
            prune_mods(config, workshop)
    finally:
        launch_config.fcntl.flock(workshop_fd, launch_config.fcntl.LOCK_UN)
        os.close(workshop_fd)


def test_prunes_tree_deeper_than_recursion_limit(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    stale = write_mod(workshop, MOD_A)
    nested = stale
    for _ in range(350):
        nested = nested / "d"
        nested.mkdir()
    config = write_config(tmp_path, [])
    recursion_limit = sys.getrecursionlimit()

    try:
        sys.setrecursionlimit(300)
        assert prune_mods(config, workshop) == [stale]
    finally:
        sys.setrecursionlimit(recursion_limit)
    assert not stale.exists()


def test_reads_server_data_with_utf8_bom(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    stale = write_mod(workshop, MOD_E, encoding="utf-8-sig")
    config = write_config(tmp_path, [])

    assert prune_mods(config, workshop) == [stale]


def test_missing_workshop_directory_is_a_no_op(tmp_path):
    config = write_config(tmp_path, [MOD_A])

    assert not prune_mods(config, tmp_path / "missing")


def test_preserves_dependencies_declared_with_mod_id_key(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    root = write_mod(workshop, MOD_A, [{"modId": MOD_B}])
    dependency = write_mod(workshop, MOD_B)
    stale = write_mod(workshop, MOD_C)
    config = write_config(tmp_path, [MOD_A])

    assert prune_mods(config, workshop) == [stale]
    assert root.exists()
    assert dependency.exists()


def test_dependency_cycle_terminates(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    first = write_mod(workshop, MOD_A, [MOD_B])
    second = write_mod(workshop, MOD_B, [MOD_A])
    stale = write_mod(workshop, MOD_C)
    config = write_config(tmp_path, [MOD_A])

    assert prune_mods(config, workshop) == [stale]
    assert first.exists()
    assert second.exists()


def test_diamond_dependencies_are_all_retained(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    root = write_mod(workshop, MOD_A, [MOD_B, MOD_C])
    left = write_mod(workshop, MOD_B, [MOD_D])
    right = write_mod(workshop, MOD_C, [MOD_D])
    shared = write_mod(workshop, MOD_D)
    stale = write_mod(workshop, MOD_E)
    config = write_config(tmp_path, [MOD_A])

    assert prune_mods(config, workshop) == [stale]
    assert root.exists()
    assert left.exists()
    assert right.exists()
    assert shared.exists()


def test_configured_mod_that_is_not_installed_is_ignored(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    stale = write_mod(workshop, MOD_B)
    config = write_config(tmp_path, [MOD_A])

    assert prune_mods(config, workshop) == [stale]
    assert not stale.exists()


def test_skips_mod_that_is_not_fully_downloaded(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    partial = write_mod(workshop, MOD_A)
    patch_revision(partial, downloaded=False)
    config = write_config(tmp_path, [])

    assert not prune_mods(config, workshop)
    assert partial.exists()


def test_skips_mod_with_non_list_dependencies(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    invalid = write_mod(workshop, MOD_A)
    patch_revision(invalid, dependencies={"id": MOD_B})
    config = write_config(tmp_path, [])

    assert not prune_mods(config, workshop)
    assert invalid.exists()


@pytest.mark.parametrize(
    "directory_name",
    ["abcdef1234567890", "111111111111111", "11111111111111111"],
)
def test_ignores_directories_that_are_not_mod_ids(tmp_path, directory_name):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    unrelated = workshop / directory_name
    unrelated.mkdir()
    (unrelated / "content.bin").write_bytes(b"content")
    config = write_config(tmp_path, [])

    assert not prune_mods(config, workshop)
    assert unrelated.exists()


def test_prunes_every_stale_mod_in_sorted_order(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    third = write_mod(workshop, MOD_C)
    first = write_mod(workshop, MOD_A)
    second = write_mod(workshop, MOD_B)
    config = write_config(tmp_path, [])

    assert prune_mods(config, workshop) == [first, second, third]
    assert not first.exists()
    assert not second.exists()
    assert not third.exists()


def test_leaves_no_quarantine_behind_when_nothing_to_prune(tmp_path):
    workshop = tmp_path / "workshop"
    workshop.mkdir()
    configured = write_mod(workshop, MOD_A)
    config = write_config(tmp_path, [MOD_A])

    assert not prune_mods(config, workshop)
    assert configured.exists()
    assert [path.name for path in workshop.iterdir()] == [MOD_A]

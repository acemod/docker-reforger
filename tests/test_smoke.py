import contextlib
import json
import os
import shutil
import subprocess

import pytest


def _run(cmd, **kwargs):
    check = kwargs.pop("check", False)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=check,
        **kwargs,
    )


def _image_tag():
    return os.environ.get(
        "ARMA_REFORGER_SMOKE_IMAGE", f"arma-reforger-smoke-{os.getpid()}"
    )


def _write_steamcmd_stub(steamcmd_dir):
    steamcmd_dir.mkdir(parents=True, exist_ok=True)
    calls_log = steamcmd_dir / "calls.log"
    with contextlib.suppress(FileNotFoundError):
        calls_log.unlink()

    script = steamcmd_dir / "steamcmd.sh"
    script.write_text(
        """#!/bin/sh
echo \"$*\" >> /steamcmd/calls.log
""",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return calls_log


def _run_container(image, dirs, *, steamcmd_dir=None, env=None):
    config_dir, profile_dir, workshop_dir = dirs
    command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{config_dir}:/reforger/Configs",
        "-v",
        f"{profile_dir}:/home/profile",
        "-v",
        f"{workshop_dir}:/reforger/workshop",
    ]
    if steamcmd_dir is not None:
        command.extend(["-v", f"{steamcmd_dir}:/steamcmd"])

    for key, value in (env or {}).items():
        command.extend(["-e", f"{key}={value}"])

    command.append(image)
    return _run(command, check=False, timeout=120)


def _make_smoke_directories(tmp_path):
    config_dir = tmp_path / "configs"
    profile_dir = tmp_path / "profile"
    workshop_dir = tmp_path / "workshop"
    steamcmd_dir = tmp_path / "steamcmd"
    steamcmd_calls = _write_steamcmd_stub(steamcmd_dir)

    for path in (config_dir, profile_dir, workshop_dir):
        path.mkdir()

    return config_dir, profile_dir, workshop_dir, steamcmd_dir, steamcmd_calls


def _run_smoke_container(tmp_path, *, skip_install):
    config_dir, profile_dir, workshop_dir, steamcmd_dir, steamcmd_calls = (
        _make_smoke_directories(tmp_path)
    )
    run = _run_container(
        _image_tag(),
        (config_dir, profile_dir, workshop_dir),
        steamcmd_dir=steamcmd_dir,
        env={
            "SKIP_INSTALL": "true" if skip_install else "false",
            "ARMA_BINARY": "/bin/true",
            "GAME_NAME": "SmokeTest",
            "GAME_MAX_PLAYERS": "16",
        },
    )

    if run.returncode != 0:
        pytest.fail(f"Smoke container failed: {run.stderr or run.stdout}")

    return config_dir, steamcmd_calls, run


def _assert_generated_config(config_dir):
    generated_config = config_dir / "docker_generated.json"
    assert generated_config.exists()

    with generated_config.open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    assert config["game"]["name"] == "SmokeTest"
    assert config["game"]["maxPlayers"] == 16


@pytest.fixture(scope="session")
def build_smoke_image():
    if shutil.which("docker") is None:
        pytest.skip("Docker is required for smoke tests")

    tag = _image_tag()
    build = _run(
        [
            "docker",
            "build",
            "-t",
            tag,
            ".",
        ],
        timeout=1200,
    )
    if build.returncode != 0:
        pytest.fail(f"Docker build failed: {build.stderr or build.stdout}")

    try:
        yield tag
    finally:
        _run(["docker", "rmi", "-f", tag], check=False)


@pytest.mark.smoke
@pytest.mark.usefixtures("build_smoke_image")
def test_dockerfile_smoke_launch_and_config_generation(tmp_path):
    config_dir, steamcmd_calls, run = _run_smoke_container(
        tmp_path,
        skip_install=True,
    )

    assert "/bin/true -config /reforger/Configs/docker_generated.json" in run.stdout

    _assert_generated_config(config_dir)
    assert not steamcmd_calls.exists()


@pytest.mark.smoke
@pytest.mark.usefixtures("build_smoke_image")
def test_dockerfile_steamcmd_update_runs_when_not_skipped(tmp_path):
    config_dir, steamcmd_calls, _ = _run_smoke_container(
        tmp_path,
        skip_install=False,
    )

    steamcmd_invocations = steamcmd_calls.read_text(encoding="utf-8").splitlines()
    assert len(steamcmd_invocations) == 2
    assert steamcmd_invocations[0] == "+login anonymous +quit"
    assert (
        steamcmd_invocations[1]
        == "+force_install_dir /reforger +login anonymous +app_update 1874900 "
        "-beta public validate +quit"
    )

    _assert_generated_config(config_dir)


@pytest.mark.smoke
@pytest.mark.usefixtures("build_smoke_image")
def test_dockerfile_builds():
    image = _image_tag()
    inspect = _run(["docker", "inspect", image], timeout=30)
    assert inspect.returncode == 0

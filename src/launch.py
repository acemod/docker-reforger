import json
import os
import random
import shlex
import signal
import subprocess
import sys
from pathlib import Path

from launch_config import bool_str, build_config, env_defined, prune_mods

# On SIGTERM, raise KeyboardInterrupt instead of exiting abruptly.
signal.signal(signal.SIGTERM, signal.default_int_handler)

CONFIG_GENERATED = "/reforger/Configs/docker_generated.json"
DEFAULT_CONFIG = "/app/docker_default.json"
EXPERIMENTAL_APPID = "1890870"
STEAMCMD = "/steamcmd/steamcmd.sh"
SENTINEL_WINDOWS_FIX = Path("/reforger/.windows_fix_done")


def random_passphrase():
    passphrase = "'"
    while "'" in passphrase:
        try:
            with open(
                "/usr/share/dict/american-english", encoding="utf-8"
            ) as word_file:
                words = word_file.readlines()
        except OSError as err:
            raise SystemExit(f"Failed to read word list: {err}") from err
        passphrase = "-".join(random.sample(words, 2)).replace("\n", "").lower()
    return passphrase


def build_steamcmd_command(force_platform=None):
    command = [STEAMCMD, "+force_install_dir", "/reforger"]
    if env_defined(os.environ, "STEAM_USER"):
        command.extend(
            ["+login", os.environ["STEAM_USER"], os.environ["STEAM_PASSWORD"]]
        )
    else:
        command.extend(["+login", "anonymous"])
    if force_platform is not None:
        command.extend(["+@sSteamCmdForcePlatformType", force_platform])
    command.extend(["+app_update", os.environ["STEAM_APPID"]])
    if env_defined(os.environ, "STEAM_BRANCH"):
        command.extend(["-beta", os.environ["STEAM_BRANCH"]])
    if env_defined(os.environ, "STEAM_BRANCH_PASSWORD"):
        command.extend(["-betapassword", os.environ["STEAM_BRANCH_PASSWORD"]])
    command.extend(["validate", "+quit"])
    return command


def build_generated_config():
    try:
        with open(DEFAULT_CONFIG, encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, ValueError) as err:
        raise SystemExit(f"Failed to load {DEFAULT_CONFIG}: {err}") from err

    config = build_config(os.environ, config)

    if not env_defined(os.environ, "GAME_PASSWORD_ADMIN"):
        config["game"]["passwordAdmin"] = random_passphrase()
        print(f"Admin password: {config['game']['passwordAdmin']}")

    try:
        with open(CONFIG_GENERATED, "w", encoding="utf-8") as config_file:
            json.dump(config, config_file, indent=4)
    except OSError as err:
        raise SystemExit(f"Failed to write {CONFIG_GENERATED}: {err}") from err

    return CONFIG_GENERATED


is_experimental = os.environ["STEAM_APPID"] == EXPERIMENTAL_APPID

# Clear Windows fix sentinel if switching away from experimental appId
if SENTINEL_WINDOWS_FIX.exists() and not is_experimental:
    SENTINEL_WINDOWS_FIX.unlink()

if os.environ["SKIP_INSTALL"] in ["", "false"]:
    # Warm up SteamCMD first. Its initial run self-updates and can exit non-zero,
    # so we get that out of the way here before the real app_update calls below.
    subprocess.call([STEAMCMD, "+login", "anonymous", "+quit"])

    if is_experimental:
        if not SENTINEL_WINDOWS_FIX.exists():
            subprocess.call(build_steamcmd_command("windows"))
            SENTINEL_WINDOWS_FIX.touch()

        subprocess.call(build_steamcmd_command("linux"))
    else:
        subprocess.call(build_steamcmd_command())

if os.environ["ARMA_CONFIG"] != "docker_generated":
    CONFIG_PATH = f"/reforger/Configs/{os.environ['ARMA_CONFIG']}"
else:
    CONFIG_PATH = build_generated_config()

if bool_str(os.environ["GAME_MODS_AUTO_PRUNE"]):
    try:
        pruned_paths = prune_mods(CONFIG_PATH, os.environ["ARMA_WORKSHOP_DIR"])
    except (OSError, ValueError) as prune_err:
        raise SystemExit(f"Failed to prune mods: {prune_err}") from prune_err
    if pruned_paths:
        print(f"Mod auto-prune removed {len(pruned_paths)} mod(s)", flush=True)
    else:
        print("Mod auto-prune: no unused mods to remove", flush=True)

launch = [
    os.environ["ARMA_BINARY"],
    "-config",
    CONFIG_PATH,
    "-backendlog",
    "-nothrow",
    "-maxFPS",
    os.environ["ARMA_MAX_FPS"],
    "-profile",
    os.environ["ARMA_PROFILE"],
    "-addonDownloadDir",
    os.environ["ARMA_WORKSHOP_DIR"],
    "-addonsDir",
    os.environ["ARMA_WORKSHOP_DIR"],
    *shlex.split(os.environ["ARMA_PARAMS"]),
]

print(shlex.join(launch), flush=True)

with subprocess.Popen(launch) as proc:
    try:
        try:
            EXIT_CODE = proc.wait()
        except KeyboardInterrupt:
            proc.send_signal(signal.SIGINT)
            EXIT_CODE = proc.wait()
    except BaseException:
        proc.kill()
        raise

sys.exit(EXIT_CODE)

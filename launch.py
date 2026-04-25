import json
import os
import random
import re
import shlex
import signal
import subprocess
import sys
from pathlib import Path

# On SIGTERM, raise KeyboardInterrupt instead of exiting abruptly.
signal.signal(signal.SIGTERM, signal.default_int_handler)

CONFIG_GENERATED = "/reforger/Configs/docker_generated.json"


def env_defined(key):
    return key in os.environ and len(os.environ[key]) > 0


def random_passphrase():
    password = "'"
    while "'" in password:
        with open("/usr/share/dict/american-english") as f:
            words = f.readlines()
        password = "-".join(random.sample(words, 2)).replace("\n", "").lower()
    return password


def bool_str(text):
    return text.lower() == "true"


SENTINEL_WINDOWS_FIX = "/reforger/.windows_fix_done"

# Clear Windows fix sentinel if switching away from experimental appId
if Path(SENTINEL_WINDOWS_FIX).exists() and os.environ["STEAM_APPID"] != "1890870":
    Path(SENTINEL_WINDOWS_FIX).unlink()

if os.environ["SKIP_INSTALL"] in ["", "false"]:
    # Special handling for experimental appId 1890870
    if os.environ["STEAM_APPID"] == "1890870":
        # We only need the Windows pass once to work around this bug. On subsequent
        # launches just perform the normal Linux update so we don't waste bandwidth.
        run_windows_pass = not Path(SENTINEL_WINDOWS_FIX).exists()

        subprocess.call(["/steamcmd/steamcmd.sh", "+login", "anonymous", "+quit"])

        if run_windows_pass:
            steamcmd_win = ["/steamcmd/steamcmd.sh"]
            steamcmd_win.extend(["+force_install_dir", "/reforger"])
            if env_defined("STEAM_USER"):
                steamcmd_win.extend(
                    ["+login", os.environ["STEAM_USER"], os.environ["STEAM_PASSWORD"]]
                )
            else:
                steamcmd_win.extend(["+login", "anonymous"])
            steamcmd_win.extend(["+@sSteamCmdForcePlatformType", "windows"])
            steamcmd_win.extend(["+app_update", os.environ["STEAM_APPID"]])
            if env_defined("STEAM_BRANCH"):
                steamcmd_win.extend(["-beta", os.environ["STEAM_BRANCH"]])
            if env_defined("STEAM_BRANCH_PASSWORD"):
                steamcmd_win.extend(
                    ["-betapassword", os.environ["STEAM_BRANCH_PASSWORD"]]
                )
            steamcmd_win.extend(["validate", "+quit"])
            subprocess.call(steamcmd_win)
            Path(SENTINEL_WINDOWS_FIX).touch()

        # Install with Linux platform
        steamcmd_linux = ["/steamcmd/steamcmd.sh"]
        steamcmd_linux.extend(["+force_install_dir", "/reforger"])
        if env_defined("STEAM_USER"):
            steamcmd_linux.extend(
                ["+login", os.environ["STEAM_USER"], os.environ["STEAM_PASSWORD"]]
            )
        else:
            steamcmd_linux.extend(["+login", "anonymous"])
        steamcmd_linux.extend(["+@sSteamCmdForcePlatformType", "linux"])
        steamcmd_linux.extend(["+app_update", os.environ["STEAM_APPID"]])
        if env_defined("STEAM_BRANCH"):
            steamcmd_linux.extend(["-beta", os.environ["STEAM_BRANCH"]])
        if env_defined("STEAM_BRANCH_PASSWORD"):
            steamcmd_linux.extend(
                ["-betapassword", os.environ["STEAM_BRANCH_PASSWORD"]]
            )
        steamcmd_linux.extend(["validate", "+quit"])
        subprocess.call(steamcmd_linux)
    else:
        # Standard installation for other appIds
        steamcmd = ["/steamcmd/steamcmd.sh"]
        steamcmd.extend(["+force_install_dir", "/reforger"])
        if env_defined("STEAM_USER"):
            steamcmd.extend(
                ["+login", os.environ["STEAM_USER"], os.environ["STEAM_PASSWORD"]]
            )
        else:
            steamcmd.extend(["+login", "anonymous"])
        steamcmd.extend(["+app_update", os.environ["STEAM_APPID"]])
        if env_defined("STEAM_BRANCH"):
            steamcmd.extend(["-beta", os.environ["STEAM_BRANCH"]])
        if env_defined("STEAM_BRANCH_PASSWORD"):
            steamcmd.extend(["-betapassword", os.environ["STEAM_BRANCH_PASSWORD"]])
        steamcmd.extend(["validate", "+quit"])
        subprocess.call(steamcmd)

if os.environ["ARMA_CONFIG"] != "docker_generated":
    config_path = f"/reforger/Configs/{os.environ['ARMA_CONFIG']}"
else:
    if os.path.exists(CONFIG_GENERATED):
        f = open(CONFIG_GENERATED)
        config = json.load(f)
        f.close()
    else:
        f = open("/docker_default.json")
        config = json.load(f)
        f.close()

    if env_defined("SERVER_BIND_ADDRESS"):
        config["bindAddress"] = os.environ["SERVER_BIND_ADDRESS"]
    if env_defined("SERVER_BIND_PORT"):
        config["bindPort"] = int(os.environ["SERVER_BIND_PORT"])
    if env_defined("SERVER_PUBLIC_ADDRESS"):
        config["publicAddress"] = os.environ["SERVER_PUBLIC_ADDRESS"]
    if env_defined("SERVER_PUBLIC_PORT"):
        config["publicPort"] = int(os.environ["SERVER_PUBLIC_PORT"])
    if env_defined("SERVER_A2S_ADDRESS") and env_defined("SERVER_A2S_PORT"):
        config["a2s"] = {
            "address": os.environ["SERVER_A2S_ADDRESS"],
            "port": int(os.environ["SERVER_A2S_PORT"]),
        }
    else:
        config["a2s"] = None

    if (
        env_defined("RCON_PASSWORD")
        and env_defined("RCON_ADDRESS")
        and env_defined("RCON_PORT")
    ):
        assert not (
            env_defined("RCON_BLACKLIST") and env_defined("RCON_WHITELIST")
        ), "RCON_BLACKLIST and RCON_WHITELIST cannot both be set"
        rcon = {
            "address": os.environ["RCON_ADDRESS"],
            "port": int(os.environ["RCON_PORT"]),
            "password": os.environ["RCON_PASSWORD"],
            "permission": os.environ["RCON_PERMISSION"],
        }
        if env_defined("RCON_MAX_CLIENTS"):
            rcon["maxClients"] = int(os.environ["RCON_MAX_CLIENTS"])
        if env_defined("RCON_BLACKLIST"):
            rcon["blacklist"] = [
                cmd.strip()
                for cmd in os.environ["RCON_BLACKLIST"].split(",")
                if cmd.strip()
            ]
        if env_defined("RCON_WHITELIST"):
            rcon["whitelist"] = [
                cmd.strip()
                for cmd in os.environ["RCON_WHITELIST"].split(",")
                if cmd.strip()
            ]
        config["rcon"] = rcon
    else:
        config["rcon"] = None

    if env_defined("GAME_NAME"):
        config["game"]["name"] = os.environ["GAME_NAME"]
    if env_defined("GAME_PASSWORD"):
        config["game"]["password"] = os.environ["GAME_PASSWORD"]
    if env_defined("GAME_PASSWORD_ADMIN"):
        config["game"]["passwordAdmin"] = os.environ["GAME_PASSWORD_ADMIN"]
    else:
        adminPassword = random_passphrase()
        config["game"]["passwordAdmin"] = adminPassword
        print(f"Admin password: {adminPassword}")
    if env_defined("GAME_ADMINS"):
        admins = str(os.environ["GAME_ADMINS"]).split(",")
        admins[:] = [admin for admin in admins if admin]  # Remove empty items form list
        config["game"]["admins"] = admins
    if env_defined("GAME_SCENARIO_ID"):
        config["game"]["scenarioId"] = os.environ["GAME_SCENARIO_ID"]
    if env_defined("GAME_MAX_PLAYERS"):
        config["game"]["maxPlayers"] = int(os.environ["GAME_MAX_PLAYERS"])
    if env_defined("GAME_VISIBLE"):
        config["game"]["visible"] = bool_str(os.environ["GAME_VISIBLE"])
    if env_defined("GAME_SUPPORTED_PLATFORMS"):
        config["game"]["supportedPlatforms"] = os.environ[
            "GAME_SUPPORTED_PLATFORMS"
        ].split(",")
    if env_defined("GAME_CROSS_PLATFORM"):
        config["game"]["crossPlatform"] = bool_str(os.environ["GAME_CROSS_PLATFORM"])
    mods_required_by_default = None
    if env_defined("GAME_MODS_REQUIRED_BY_DEFAULT"):
        mods_required_by_default = bool_str(os.environ["GAME_MODS_REQUIRED_BY_DEFAULT"])
        config["game"]["modsRequiredByDefault"] = mods_required_by_default
    if env_defined("GAME_PROPS_BATTLEYE"):
        config["game"]["gameProperties"]["battlEye"] = bool_str(
            os.environ["GAME_PROPS_BATTLEYE"]
        )
    if env_defined("GAME_PROPS_DISABLE_THIRD_PERSON"):
        config["game"]["gameProperties"]["disableThirdPerson"] = bool_str(
            os.environ["GAME_PROPS_DISABLE_THIRD_PERSON"]
        )
    if env_defined("GAME_PROPS_FAST_VALIDATION"):
        config["game"]["gameProperties"]["fastValidation"] = bool_str(
            os.environ["GAME_PROPS_FAST_VALIDATION"]
        )
    if env_defined("GAME_PROPS_SERVER_MAX_VIEW_DISTANCE"):
        config["game"]["gameProperties"]["serverMaxViewDistance"] = int(
            os.environ["GAME_PROPS_SERVER_MAX_VIEW_DISTANCE"]
        )
    if env_defined("GAME_PROPS_SERVER_MIN_GRASS_DISTANCE"):
        config["game"]["gameProperties"]["serverMinGrassDistance"] = int(
            os.environ["GAME_PROPS_SERVER_MIN_GRASS_DISTANCE"]
        )
    if env_defined("GAME_PROPS_NETWORK_VIEW_DISTANCE"):
        config["game"]["gameProperties"]["networkViewDistance"] = int(
            os.environ["GAME_PROPS_NETWORK_VIEW_DISTANCE"]
        )
    if env_defined("GAME_PROPS_VON_DISABLE_UI"):
        config["game"]["gameProperties"]["VONDisableUI"] = bool_str(
            os.environ["GAME_PROPS_VON_DISABLE_UI"]
        )
    if env_defined("GAME_PROPS_VON_DISABLE_DIRECT_SPEECH_UI"):
        config["game"]["gameProperties"]["VONDisableDirectSpeechUI"] = bool_str(
            os.environ["GAME_PROPS_VON_DISABLE_DIRECT_SPEECH_UI"]
        )
    if env_defined("GAME_PROPS_VON_CAN_TRANSMIT_CROSS_FACTION"):
        config["game"]["gameProperties"]["VONCanTransmitCrossFaction"] = bool_str(
            os.environ["GAME_PROPS_VON_CAN_TRANSMIT_CROSS_FACTION"]
        )

    if env_defined("GAME_MISSION_HEADER_JSON_FILE_PATH"):
        with open(os.environ["GAME_MISSION_HEADER_JSON_FILE_PATH"]) as f:
            config["game"]["gameProperties"]["missionHeader"] = json.load(f)

    # Since we want to keep ENVs as a single source of truth
    # we will regenerate the mod list in case any manual changes were made
    # also deletes the mod entries when GAME_MODS_IDS_LIST is empty
    config["game"]["mods"] = []
    config_mod_ids = []
    if env_defined("GAME_MODS_IDS_LIST"):
        reg = re.compile(r"^[A-Z\d,=.]+$")
        assert reg.match(
            str(os.environ["GAME_MODS_IDS_LIST"])
        ), "Illegal characters in GAME_MODS_IDS_LIST env"
        mods = str(os.environ["GAME_MODS_IDS_LIST"]).split(",")
        mods[:] = [mod for mod in mods if mod]  # Remove empty items form list
        reg = re.compile(r"^\d+\.\d+\.\d+$")
        for mod in mods:
            mod_details = mod.split("=")
            assert 0 < len(mod_details) < 3, f"{mod} mod not defined properly"
            mod_id = mod_details[0]
            if mod_id in config_mod_ids:
                continue  # modId already defined in config, skipping to avoid duplicates
            mod_config = {"modId": mod_id}
            if len(mod_details) == 2:
                assert reg.match(
                    mod_details[1]
                ), f"{mod} mod version does not match the pattern"
                mod_config["version"] = mod_details[1]
            if mods_required_by_default is not None:
                mod_config["required"] = mods_required_by_default
            config_mod_ids.append(mod_id)
            config["game"]["mods"].append(mod_config)
    if env_defined("GAME_MODS_JSON_FILE_PATH"):
        with open(os.environ["GAME_MODS_JSON_FILE_PATH"]) as f:
            json_mods = json.load(f)
            allowed_keys = ["modId", "name", "version", "required"]
            for provided_mod in json_mods:
                assert (
                    "modId" in provided_mod
                ), f"Entry in GAME_MODS_JSON_FILE_PATH file does not contain modId: {provided_mod}"
                if provided_mod["modId"] in config_mod_ids:
                    continue  # modId already defined in config, skipping to avoid duplicates
                valid_mod = {
                    key: provided_mod[key]
                    for key in allowed_keys
                    if key in provided_mod
                }  # Extract only valid config keys
                if mods_required_by_default is not None and "required" not in valid_mod:
                    valid_mod["required"] = mods_required_by_default
                config_mod_ids.append(provided_mod["modId"])
                config["game"]["mods"].append(valid_mod)

    # Persistence (only added when at least one persistence ENV is defined)
    persistence_defined = (
        env_defined("PERSISTENCE_AUTO_SAVE_INTERVAL")
        or env_defined("PERSISTENCE_HIVE_ID")
        or env_defined("PERSISTENCE_JSON_FILE_PATH")
    )
    if persistence_defined:
        persistence = {}
        if env_defined("PERSISTENCE_AUTO_SAVE_INTERVAL"):
            persistence["autoSaveInterval"] = int(
                os.environ["PERSISTENCE_AUTO_SAVE_INTERVAL"]
            )
        if env_defined("PERSISTENCE_HIVE_ID"):
            persistence["hiveId"] = int(os.environ["PERSISTENCE_HIVE_ID"])
        if env_defined("PERSISTENCE_JSON_FILE_PATH"):
            with open(os.environ["PERSISTENCE_JSON_FILE_PATH"]) as f:
                persistence_json = json.load(f)
                allowed_keys = ["databases", "storages"]
                for key in allowed_keys:
                    if key in persistence_json:
                        persistence[key] = persistence_json[key]
        config["game"]["gameProperties"]["persistence"] = persistence

    # Operating (only added when at least one operating ENV is defined)
    operating = {}
    if env_defined("OPERATING_LOBBY_PLAYER_SYNCHRONISE"):
        operating["lobbyPlayerSynchronise"] = bool_str(
            os.environ["OPERATING_LOBBY_PLAYER_SYNCHRONISE"]
        )
    if env_defined("OPERATING_DISABLE_CRASH_REPORTER"):
        operating["disableCrashReporter"] = bool_str(
            os.environ["OPERATING_DISABLE_CRASH_REPORTER"]
        )
    if env_defined("OPERATING_DISABLE_NAVMESH_STREAMING"):
        val = os.environ["OPERATING_DISABLE_NAVMESH_STREAMING"]
        if val.lower() == "all":
            operating["disableNavmeshStreaming"] = []
        else:
            operating["disableNavmeshStreaming"] = [
                name.strip() for name in val.split(",") if name.strip()
            ]
    if env_defined("OPERATING_DISABLE_SERVER_SHUTDOWN"):
        operating["disableServerShutdown"] = bool_str(
            os.environ["OPERATING_DISABLE_SERVER_SHUTDOWN"]
        )
    if env_defined("OPERATING_DISABLE_AI"):
        operating["disableAI"] = bool_str(os.environ["OPERATING_DISABLE_AI"])
    if env_defined("OPERATING_PLAYER_SAVE_TIME"):
        operating["playerSaveTime"] = int(os.environ["OPERATING_PLAYER_SAVE_TIME"])
    if env_defined("OPERATING_AI_LIMIT"):
        operating["aiLimit"] = int(os.environ["OPERATING_AI_LIMIT"])
    if env_defined("OPERATING_SLOT_RESERVATION_TIMEOUT"):
        operating["slotReservationTimeout"] = int(
            os.environ["OPERATING_SLOT_RESERVATION_TIMEOUT"]
        )
    if env_defined("OPERATING_JOIN_QUEUE_MAX_SIZE"):
        operating["joinQueue"] = {
            "maxSize": int(os.environ["OPERATING_JOIN_QUEUE_MAX_SIZE"])
        }
    if operating:
        config["operating"] = operating

    f = open(CONFIG_GENERATED, "w")
    json.dump(config, f, indent=4)
    f.close()

    config_path = CONFIG_GENERATED

launch = [
    os.environ["ARMA_BINARY"],
    "-config",
    config_path,
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

proc = subprocess.Popen(launch)

try:
    try:
        sys.exit(proc.wait())
    except KeyboardInterrupt:
        proc.send_signal(signal.SIGINT)
        sys.exit(proc.wait())
except SystemExit:
    raise
except BaseException:
    proc.kill()
    raise

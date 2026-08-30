import json

import pytest

from src.launch_config import bool_str, build_config, env_defined

MOD_A = "1111111111111111"
MOD_B = "2222222222222222"


def write_json(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(json.dumps(content))
    return path


def test_env_defined():
    assert env_defined({"FOO": "bar"}, "FOO")
    assert not env_defined({"FOO": ""}, "FOO")
    assert not env_defined({}, "FOO")


def test_bool_str():
    assert bool_str("true")
    assert bool_str("TRUE")
    assert bool_str("True")
    assert not bool_str("false")
    assert not bool_str("")
    assert not bool_str("yes")
    assert bool_str(" true ")
    assert bool_str(" true")
    assert bool_str("true ")
    assert bool_str("\ttrue\n")
    assert not bool_str(" false ")
    assert not bool_str(" yes ")


def test_defaults_preserved(base_config):
    env = {}
    config = build_config(env, base_config)
    assert config["game"]["name"] == "Arma Reforger Docker Server"
    assert config["game"]["maxPlayers"] == 64
    assert config["bindPort"] == 2001


def test_server_overrides(base_config):
    env = {
        "SERVER_BIND_ADDRESS": "127.0.0.1",
        "SERVER_BIND_PORT": "3001",
        "SERVER_PUBLIC_ADDRESS": "1.2.3.4",
        "SERVER_PUBLIC_PORT": "3002",
    }
    config = build_config(env, base_config)
    assert config["bindAddress"] == "127.0.0.1"
    assert config["bindPort"] == 3001
    assert config["publicAddress"] == "1.2.3.4"
    assert config["publicPort"] == 3002


def test_a2s_config(base_config):
    env = {
        "SERVER_A2S_ADDRESS": "0.0.0.0",
        "SERVER_A2S_PORT": "17777",
    }
    config = build_config(env, base_config)
    assert config["a2s"]["address"] == "0.0.0.0"
    assert config["a2s"]["port"] == 17777


def test_a2s_removed_when_partial(base_config):
    env = {"SERVER_A2S_ADDRESS": "0.0.0.0"}
    config = build_config(env, base_config)
    assert "a2s" not in config


def test_rcon_config(base_config):
    env = {
        "RCON_ADDRESS": "0.0.0.0",
        "RCON_PORT": "19999",
        "RCON_PASSWORD": "secret",
        "RCON_PERMISSION": "admin",
        "RCON_MAX_CLIENTS": "10",
    }
    config = build_config(env, base_config)
    assert config["rcon"]["address"] == "0.0.0.0"
    assert config["rcon"]["port"] == 19999
    assert config["rcon"]["password"] == "secret"
    assert config["rcon"]["permission"] == "admin"
    assert config["rcon"]["maxClients"] == 10


def test_rcon_permission_defaults_to_admin(base_config):
    env = {
        "RCON_ADDRESS": "0.0.0.0",
        "RCON_PORT": "19999",
        "RCON_PASSWORD": "secret",
    }
    config = build_config(env, base_config)
    assert config["rcon"]["permission"] == "admin"


def test_rcon_blacklist(base_config):
    env = {
        "RCON_ADDRESS": "0.0.0.0",
        "RCON_PORT": "19999",
        "RCON_PASSWORD": "secret",
        "RCON_PERMISSION": "admin",
        "RCON_BLACKLIST": "kick,ban",
    }
    config = build_config(env, base_config)
    assert config["rcon"]["blacklist"] == ["kick", "ban"]


def test_rcon_whitelist(base_config):
    env = {
        "RCON_ADDRESS": "0.0.0.0",
        "RCON_PORT": "19999",
        "RCON_PASSWORD": "secret",
        "RCON_PERMISSION": "admin",
        "RCON_WHITELIST": "help,status",
    }
    config = build_config(env, base_config)
    assert config["rcon"]["whitelist"] == ["help", "status"]


def test_rcon_blacklist_and_whitelist_fails(base_config):
    env = {
        "RCON_ADDRESS": "0.0.0.0",
        "RCON_PORT": "19999",
        "RCON_PASSWORD": "secret",
        "RCON_PERMISSION": "admin",
        "RCON_BLACKLIST": "kick",
        "RCON_WHITELIST": "help",
    }
    with pytest.raises(ValueError, match="cannot both be set"):
        build_config(env, base_config)


def test_game_overrides(base_config):
    env = {
        "GAME_NAME": "My Server",
        "GAME_PASSWORD": "mypassword",
        "GAME_SCENARIO_ID": "{FOO}Missions/01.conf",
        "GAME_MAX_PLAYERS": "32",
        "GAME_VISIBLE": "false",
        "GAME_CROSS_PLATFORM": "true",
    }
    config = build_config(env, base_config)
    assert config["game"]["name"] == "My Server"
    assert config["game"]["password"] == "mypassword"
    assert config["game"]["scenarioId"] == "{FOO}Missions/01.conf"
    assert config["game"]["maxPlayers"] == 32
    assert not config["game"]["visible"]
    assert config["game"]["crossPlatform"]


def test_game_admins(base_config):
    env = {"GAME_ADMINS": "admin1,admin2,,admin3"}
    config = build_config(env, base_config)
    assert config["game"]["admins"] == ["admin1", "admin2", "admin3"]


def test_game_supported_platforms(base_config):
    env = {"GAME_SUPPORTED_PLATFORMS": "PLATFORM_PC,PLATFORM_XBL"}
    config = build_config(env, base_config)
    assert config["game"]["supportedPlatforms"] == ["PLATFORM_PC", "PLATFORM_XBL"]


def test_mods_required_by_default(base_config):
    env = {"GAME_MODS_REQUIRED_BY_DEFAULT": "true"}
    config = build_config(env, base_config)
    assert config["game"]["modsRequiredByDefault"]


def test_mods_ids_list(base_config):
    env = {"GAME_MODS_IDS_LIST": f"{MOD_A}=1.0.0,{MOD_B}"}
    config = build_config(env, base_config)
    assert len(config["game"]["mods"]) == 2
    assert config["game"]["mods"][0] == {"modId": MOD_A, "version": "1.0.0"}
    assert config["game"]["mods"][1] == {"modId": MOD_B}


def test_mods_ids_list_with_required(base_config):
    env = {
        "GAME_MODS_IDS_LIST": f"{MOD_A}=1.0.0",
        "GAME_MODS_REQUIRED_BY_DEFAULT": "true",
    }
    config = build_config(env, base_config)
    assert config["game"]["mods"][0]["required"]


def test_mods_ids_list_invalid_chars(base_config):
    env = {"GAME_MODS_IDS_LIST": f"{MOD_A}=1.0.0;bad"}
    with pytest.raises(ValueError, match="Illegal characters"):
        build_config(env, base_config)


def test_mods_ids_list_invalid_id(base_config):
    env = {"GAME_MODS_IDS_LIST": "12345"}
    with pytest.raises(ValueError, match="Invalid mod ID"):
        build_config(env, base_config)


def test_mods_ids_list_invalid_version(base_config):
    env = {"GAME_MODS_IDS_LIST": f"{MOD_A}=BADVERSION"}
    with pytest.raises(ValueError, match="version does not match"):
        build_config(env, base_config)


def test_mods_json_file(base_config, tmp_path):
    mods_file = write_json(
        tmp_path,
        "mods.json",
        [
            {"modId": MOD_A, "name": "Test Mod", "version": "1.0.0"},
            {"modId": MOD_B, "required": False},
        ],
    )
    env = {"GAME_MODS_JSON_FILE_PATH": str(mods_file)}
    config = build_config(env, base_config)
    assert len(config["game"]["mods"]) == 2
    assert config["game"]["mods"][0]["name"] == "Test Mod"
    assert not config["game"]["mods"][1]["required"]


def test_mods_json_missing_modid(base_config, tmp_path):
    mods_file = write_json(tmp_path, "mods.json", [{"name": "Bad Mod"}])
    env = {"GAME_MODS_JSON_FILE_PATH": str(mods_file)}
    with pytest.raises(ValueError, match="does not contain modId"):
        build_config(env, base_config)


def test_mods_json_invalid_mod_id(base_config, tmp_path):
    mods_file = write_json(tmp_path, "mods.json", [{"modId": "12345"}])
    env = {"GAME_MODS_JSON_FILE_PATH": str(mods_file)}
    with pytest.raises(ValueError, match="Invalid mod ID"):
        build_config(env, base_config)


def test_mods_json_must_be_array(base_config, tmp_path):
    mods_file = write_json(tmp_path, "mods.json", {"modId": MOD_A})
    env = {"GAME_MODS_JSON_FILE_PATH": str(mods_file)}
    with pytest.raises(ValueError, match="must contain an array"):
        build_config(env, base_config)


def test_mods_deduplication(base_config, tmp_path):
    """Mod IDs from GAME_MODS_IDS_LIST should skip duplicates from JSON."""
    mods_file = write_json(
        tmp_path, "mods.json", [{"modId": MOD_A, "name": "From JSON"}]
    )
    env = {
        "GAME_MODS_IDS_LIST": MOD_A,
        "GAME_MODS_JSON_FILE_PATH": str(mods_file),
    }
    config = build_config(env, base_config)
    assert len(config["game"]["mods"]) == 1


def test_persistence_config(base_config):
    env = {
        "PERSISTENCE_AUTO_SAVE_INTERVAL": "300",
        "PERSISTENCE_SAVE_RETENTION": "5",
        "PERSISTENCE_LOAD_SESSION_SAVE": "true",
        "PERSISTENCE_KEEP_SESSION_SAVE": "false",
        "PERSISTENCE_HIVE_ID": "123",
    }
    config = build_config(env, base_config)
    persistence = config["game"]["gameProperties"]["persistence"]
    assert persistence["autoSaveInterval"] == 300
    assert persistence["saveRetention"] == 5
    assert persistence["loadSessionSave"]
    assert not persistence["keepSessionSave"]
    assert persistence["hiveId"] == 123


def test_persistence_json_merge(base_config, tmp_path):
    persistence_file = write_json(
        tmp_path,
        "persistence.json",
        {
            "databases": {"foo": "bar"},
            "storages": {"baz": "qux"},
            "ignored": "should not appear",
        },
    )
    env = {"PERSISTENCE_JSON_FILE_PATH": str(persistence_file)}
    config = build_config(env, base_config)
    persistence = config["game"]["gameProperties"]["persistence"]
    assert persistence["databases"] == {"foo": "bar"}
    assert persistence["storages"] == {"baz": "qux"}
    assert "ignored" not in persistence


def test_persistence_not_set_when_empty(base_config):
    """When no persistence envs are set, key should not be added."""
    env = {}
    config = build_config(env, base_config)
    assert "persistence" not in config["game"]["gameProperties"]


def test_persistence_removed_when_env_cleared(base_config):
    previous = build_config({"PERSISTENCE_HIVE_ID": "123"}, base_config)
    config = build_config({}, previous)
    assert "persistence" not in config["game"]["gameProperties"]


def test_operating_config(base_config):
    env = {
        "OPERATING_LOBBY_PLAYER_SYNCHRONISE": "true",
        "OPERATING_DISABLE_CRASH_REPORTER": "false",
        "OPERATING_DISABLE_SERVER_SHUTDOWN": "true",
        "OPERATING_DISABLE_AI": "false",
        "OPERATING_PLAYER_SAVE_TIME": "120",
        "OPERATING_AI_LIMIT": "50",
        "OPERATING_SLOT_RESERVATION_TIMEOUT": "60",
        "OPERATING_JOIN_QUEUE_MAX_SIZE": "10",
    }
    config = build_config(env, base_config)
    operating = config["operating"]
    assert operating["lobbyPlayerSynchronise"]
    assert not operating["disableCrashReporter"]
    assert operating["disableServerShutdown"]
    assert not operating["disableAI"]
    assert operating["playerSaveTime"] == 120
    assert operating["aiLimit"] == 50
    assert operating["slotReservationTimeout"] == 60
    assert operating["joinQueue"]["maxSize"] == 10


def test_operating_navmesh_all(base_config):
    env = {"OPERATING_DISABLE_NAVMESH_STREAMING": "all"}
    config = build_config(env, base_config)
    assert config["operating"]["disableNavmeshStreaming"] == []


def test_operating_navmesh_list(base_config):
    env = {"OPERATING_DISABLE_NAVMESH_STREAMING": "foo,bar,baz"}
    config = build_config(env, base_config)
    assert config["operating"]["disableNavmeshStreaming"] == ["foo", "bar", "baz"]


def test_operating_not_set_when_empty(base_config):
    """When no operating envs are set, key should not be added."""
    env = {}
    config = build_config(env, base_config)
    assert "operating" not in config


def test_operating_removed_when_env_cleared(base_config):
    previous = build_config({"OPERATING_AI_LIMIT": "50"}, base_config)
    config = build_config({}, previous)
    assert "operating" not in config


def test_mission_header_json(base_config, tmp_path):
    mission_file = write_json(tmp_path, "mission.json", {"myKey": "myValue"})
    env = {"GAME_MISSION_HEADER_JSON_FILE_PATH": str(mission_file)}
    config = build_config(env, base_config)
    assert config["game"]["gameProperties"]["missionHeader"] == {"myKey": "myValue"}


def test_mission_header_reset_when_env_cleared(base_config, tmp_path):
    mission_file = write_json(tmp_path, "mission.json", {"myKey": "myValue"})
    previous = build_config(
        {"GAME_MISSION_HEADER_JSON_FILE_PATH": str(mission_file)}, base_config
    )
    config = build_config({}, previous)
    assert config["game"]["gameProperties"]["missionHeader"] == {}


def test_game_properties_booleans(base_config):
    env = {
        "GAME_PROPS_BATTLEYE": "false",
        "GAME_PROPS_DISABLE_THIRD_PERSON": "true",
        "GAME_PROPS_FAST_VALIDATION": "false",
        "GAME_PROPS_VON_DISABLE_UI": "true",
        "GAME_PROPS_VON_DISABLE_DIRECT_SPEECH_UI": "true",
        "GAME_PROPS_VON_CAN_TRANSMIT_CROSS_FACTION": "true",
    }
    config = build_config(env, base_config)
    game_properties = config["game"]["gameProperties"]
    assert not game_properties["battlEye"]
    assert game_properties["disableThirdPerson"]
    assert not game_properties["fastValidation"]
    assert game_properties["VONDisableUI"]
    assert game_properties["VONDisableDirectSpeechUI"]
    assert game_properties["VONCanTransmitCrossFaction"]


def test_game_properties_integers(base_config):
    env = {
        "GAME_PROPS_SERVER_MAX_VIEW_DISTANCE": "3000",
        "GAME_PROPS_SERVER_MIN_GRASS_DISTANCE": "100",
        "GAME_PROPS_NETWORK_VIEW_DISTANCE": "2000",
    }
    config = build_config(env, base_config)
    game_properties = config["game"]["gameProperties"]
    assert game_properties["serverMaxViewDistance"] == 3000
    assert game_properties["serverMinGrassDistance"] == 100
    assert game_properties["networkViewDistance"] == 2000


RCON_ENV = {
    "RCON_ADDRESS": "0.0.0.0",
    "RCON_PORT": "19999",
    "RCON_PASSWORD": "secret",
}

# Every env var build_config maps onto the config, with a value that differs
# from the default. Anything dropped from the env maps stops having an effect,
# which is what this catches.
ENV_OVERRIDES = [
    {"SERVER_BIND_ADDRESS": "127.0.0.1"},
    {"SERVER_BIND_PORT": "3001"},
    {"SERVER_PUBLIC_ADDRESS": "1.2.3.4"},
    {"SERVER_PUBLIC_PORT": "3002"},
    {"SERVER_A2S_ADDRESS": "127.0.0.1", "SERVER_A2S_PORT": "17777"},
    RCON_ENV,
    RCON_ENV | {"RCON_PERMISSION": "monitor"},
    RCON_ENV | {"RCON_MAX_CLIENTS": "10"},
    RCON_ENV | {"RCON_BLACKLIST": "kick"},
    RCON_ENV | {"RCON_WHITELIST": "help"},
    {"GAME_NAME": "My Server"},
    {"GAME_PASSWORD": "mypassword"},
    {"GAME_PASSWORD_ADMIN": "myadminpassword"},
    {"GAME_ADMINS": "admin1,admin2"},
    {"GAME_SCENARIO_ID": "{FOO}Missions/01.conf"},
    {"GAME_MAX_PLAYERS": "32"},
    {"GAME_VISIBLE": "false"},
    {"GAME_SUPPORTED_PLATFORMS": "PLATFORM_PC"},
    {"GAME_CROSS_PLATFORM": "true"},
    {"GAME_MODS_REQUIRED_BY_DEFAULT": "true"},
    {"GAME_MODS_IDS_LIST": MOD_A},
    {"GAME_PROPS_BATTLEYE": "false"},
    {"GAME_PROPS_DISABLE_THIRD_PERSON": "true"},
    {"GAME_PROPS_FAST_VALIDATION": "false"},
    {"GAME_PROPS_SERVER_MAX_VIEW_DISTANCE": "3000"},
    {"GAME_PROPS_SERVER_MIN_GRASS_DISTANCE": "100"},
    {"GAME_PROPS_NETWORK_VIEW_DISTANCE": "2000"},
    {"GAME_PROPS_VON_DISABLE_UI": "true"},
    {"GAME_PROPS_VON_DISABLE_DIRECT_SPEECH_UI": "true"},
    {"GAME_PROPS_VON_CAN_TRANSMIT_CROSS_FACTION": "true"},
    {"PERSISTENCE_AUTO_SAVE_INTERVAL": "300"},
    {"PERSISTENCE_SAVE_RETENTION": "5"},
    {"PERSISTENCE_LOAD_SESSION_SAVE": "true"},
    {"PERSISTENCE_KEEP_SESSION_SAVE": "true"},
    {"PERSISTENCE_HIVE_ID": "123"},
    {"OPERATING_LOBBY_PLAYER_SYNCHRONISE": "true"},
    {"OPERATING_DISABLE_CRASH_REPORTER": "true"},
    {"OPERATING_DISABLE_NAVMESH_STREAMING": "all"},
    {"OPERATING_DISABLE_SERVER_SHUTDOWN": "true"},
    {"OPERATING_DISABLE_AI": "true"},
    {"OPERATING_PLAYER_SAVE_TIME": "120"},
    {"OPERATING_AI_LIMIT": "50"},
    {"OPERATING_SLOT_RESERVATION_TIMEOUT": "60"},
    {"OPERATING_JOIN_QUEUE_MAX_SIZE": "10"},
]


@pytest.mark.parametrize("env", ENV_OVERRIDES, ids=lambda env: ",".join(sorted(env)))
def test_env_override_reaches_the_config(base_config, env):
    assert build_config(env, base_config) != build_config({}, base_config)

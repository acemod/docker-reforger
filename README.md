# Arma Reforger Dedicated Server

An Arma Reforger dedicated server. Updates to the latest version every time it is restarted.

## Usage

### Docker CLI

```sh
    docker create \
        --name=reforger-server \
        -p 2001:2001/udp \
        -v path/to/configs:/reforger/Configs \
        -v path/to/profiles:/home/profile \
        -v path/to/workshop:/reforger/workshop \
        -e SERVER_PUBLIC_ADDRESS="public ip" \
        -e GAME_NAME="My Docker Reforger Server" \
        ghcr.io/acemod/arma-reforger:latest
```

If an admin password is not provided, one will be generated and printed to the console.

### Docker-compose

Simply check-out / copy [the provided docker-compose.yml](docker-compose.yml) and adjust to your personal needs.

## Parameters

### Configs

By default the configs are generated from the ENV variables in the Dockerfile. After the first run the file can be expanded with additional options manually, but the fields will always be overwritten by the ENV variables.

Alternatively, change the `ARMA_CONFIG` variable to a file present in the `Configs` volume. It will be used without modification.

### Steam / Installation

| Variable | Default | Description |
|---|---|---|
| `STEAM_USER` | *(empty)* | Steam username (anonymous login if empty) |
| `STEAM_PASSWORD` | *(empty)* | Steam password |
| `STEAM_APPID` | `1874900` | Steam app ID. Use `1890870` for the experimental server |
| `STEAM_BRANCH` | `public` | Steam branch to install from |
| `STEAM_BRANCH_PASSWORD` | *(empty)* | Password for the Steam branch |
| `SKIP_INSTALL` | `false` | Skip the SteamCMD install/update step |

### Server / Network

| Variable | Default | Description |
|---|---|---|
| `ARMA_CONFIG` | `docker_generated` | Config file name (without `.json`). Set to use a custom config from the `Configs` volume without ENV overrides |
| `ARMA_PROFILE` | `/home/profile` | Server profile directory |
| `ARMA_BINARY` | `./ArmaReforgerServer` | Path to the server binary |
| `ARMA_PARAMS` | *(empty)* | Additional command-line parameters (e.g. `-loadSessionSave` to resume a previous session) |
| `ARMA_MAX_FPS` | `120` | Maximum server FPS |
| `ARMA_WORKSHOP_DIR` | `/reforger/workshop` | Workshop / addons directory |
| `SERVER_BIND_ADDRESS` | `0.0.0.0` | Address the server binds to |
| `SERVER_BIND_PORT` | `2001` | Port the server binds to (UDP) |
| `SERVER_PUBLIC_ADDRESS` | *(empty)* | Public IP address for server browser |
| `SERVER_PUBLIC_PORT` | `2001` | Public port for server browser |
| `SERVER_A2S_ADDRESS` | `0.0.0.0` | A2S query address. Set both address and port to enable; leave either empty to disable |
| `SERVER_A2S_PORT` | `17777` | A2S query port (UDP) |

**NOTE**: The full list of [Startup Parameters](https://community.bistudio.com/wiki/Arma_Reforger:Startup_Parameters#Hosting) for `ARMA_PARAMS` can be found on the Arma Reforger wiki.

### RCON

RCON is activated by defining the `RCON_PASSWORD` variable.

| Variable | Default | Description |
|---|---|---|
| `RCON_ADDRESS` | `0.0.0.0` | RCON bind address |
| `RCON_PORT` | `19999` | RCON port (UDP) |
| `RCON_PASSWORD` | *(empty)* | RCON password. Required for RCON to start. Must be at least 3 characters, no spaces |
| `RCON_PERMISSION` | `admin` | [Permission](https://community.bistudio.com/wiki/Arma_Reforger:Server_Config#permission) level for all RCON clients |

### Game

| Variable | Default | Description |
|---|---|---|
| `GAME_NAME` | `Arma Reforger Docker Server` | Server name shown in the server browser |
| `GAME_PASSWORD` | *(empty)* | Password required to join the server |
| `GAME_PASSWORD_ADMIN` | *(auto-generated)* | Admin password. If not set, a random passphrase is generated and printed to the console |
| `GAME_ADMINS` | *(empty)* | Comma-delimited list of admin identityIds and/or steamIds |
| `GAME_SCENARIO_ID` | `{ECC61978EDCC2B5A}Missions/23_Campaign.conf` | Scenario to load |
| `GAME_MAX_PLAYERS` | `32` | Maximum number of players |
| `GAME_VISIBLE` | `true` | Whether the server is visible in the server browser |
| `GAME_SUPPORTED_PLATFORMS` | `PLATFORM_PC,PLATFORM_XBL,PLATFORM_PSN` | Comma-separated list of supported platforms |
| `GAME_MODS_IDS_LIST` | *(empty)* | Comma-separated mod IDs with optional version (e.g. `5965770215E93269=1.0.6,5965550F24A0C152`) |
| `GAME_MODS_JSON_FILE_PATH` | *(empty)* | Path to a JSON file containing an array of mod objects (see [Mods](#mods)) |

### Game Properties

| Variable | Default | Description |
|---|---|---|
| `GAME_PROPS_BATTLEYE` | `true` | Enable BattlEye anti-cheat |
| `GAME_PROPS_DISABLE_THIRD_PERSON` | `false` | Disable third-person camera |
| `GAME_PROPS_FAST_VALIDATION` | `true` | Enable fast addon validation |
| `GAME_PROPS_SERVER_MAX_VIEW_DISTANCE` | `2500` | Maximum view distance (meters) |
| `GAME_PROPS_SERVER_MIN_GRASS_DISTANCE` | `50` | Minimum grass render distance (meters) |
| `GAME_PROPS_NETWORK_VIEW_DISTANCE` | `1000` | Network view distance (meters) |
| `GAME_PROPS_VON_DISABLE_UI` | `false` | Disable VON UI |
| `GAME_PROPS_VON_DISABLE_DIRECT_SPEECH_UI` | `false` | Disable VON direct speech UI |
| `GAME_PROPS_VON_CAN_TRANSMIT_CROSS_FACTION` | `false` | Allow cross-faction VON transmission |

### Persistence

Persistence is **disabled by default** — the system works automatically for most use cases. Set any `PERSISTENCE_*` variable to enable the persistence config section.

**NOTE**: ``-loadSessionSave`` must be enabled in order to load session saves. 

| Variable | Default | Description |
|---|---|---|
| `PERSISTENCE_AUTO_SAVE_INTERVAL` | *(empty)* | Minutes between auto-saves (0–60). 0 disables auto-save. Server default is 10 |
| `PERSISTENCE_HIVE_ID` | *(empty)* | Hive identifier (0–16383). Used when multiple servers share a persistence database |
| `PERSISTENCE_JSON_FILE_PATH` | *(empty)* | Path to a JSON file containing `databases` and/or `storages` objects (see below) |

For advanced persistence setups (external databases, custom storages), create a JSON file with `databases` and/or `storages` objects and mount it into the container:

```sh
-v ${PWD}/persistence.json:/persistence.json
-e PERSISTENCE_JSON_FILE_PATH="/persistence.json"
-e PERSISTENCE_AUTO_SAVE_INTERVAL=15
```

Example `persistence.json`:

```json
{
  "databases": {
    "webapi": {
      "preset": "{0123456789ABCDEF}Configs/Systems/Persistence/Database/JsonWebApi.conf",
      "options": {
        "url": "https://persistence-db.example.com:5539/api/v1",
        "headers": {
          "X-API-KEY": "your-api-key",
          "Content-Type": "application/json"
        }
      }
    }
  },
  "storages": {
    "session": {
      "database": "webapi"
    }
  }
}
```

**Documentation**:
- [Persistence](https://community.bistudio.com/wiki/Arma_Reforger:Persistence_System) 
- [Persistence Server Configuration](https://community.bistudio.com/wiki/Arma_Reforger:Server_Config#persistence)

### Mods

Workshop mods can be defined in two ways. You can use both or either of those.

#### GAME_MODS_IDS_LIST

A comma separated list of IDs, with an optional version.

```sh
-e GAME_MODS_IDS_LIST="5965770215E93269=1.0.6,5965550F24A0C152"
```

#### GAME_MODS_JSON_FILE_PATH

Path to a JSON file that contains array of mod objects.

```sh
-v ${PWD}/mods_file.json:/mods_file.json
-e GAME_MODS_JSON_FILE_PATH="/mods_file.json"
```

```json
[
  {
    "modId": "597706449575D90B",
    "version": "1.1.1"
  }
]
```

### Documentation

The full Server Configuration can be found [here](https://community.bistudio.com/wiki/Arma_Reforger:Server_Config).  
The Dockerfile may not include every option that is currently available and may need updated and may require being updated for additional support of features.

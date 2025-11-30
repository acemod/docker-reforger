# Configuration

Learn how to configure your Arma Reforger Dedicated Server using environment variables and configuration files.

---

## Environment Variables

Here is the original markdown table, with the "Description" column placed back into the table, but with the table itself made more compact and readable. The columns have been resized to fit the content better.

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| **`ARMA_BINARY`** | `./ArmaReforgerServer` | Path to the server binary. |
| **`ARMA_CONFIG`** | `docker_generated` | Path to the server configuration file. |
| **`ARMA_MAX_FPS`** | `120` | Maximum server FPS. |
| **`ARMA_PARAMS`** | (empty) | Additional parameters to pass to the server binary. |
| **`ARMA_PROFILE`** | `/home/profile` | Path to the server profile directory. |
| **`ARMA_WORKSHOP_DIR`** | `/reforger/workshop` | Path to the workshop directory. |
| **`GAME_ADMINS`** | (empty) | Comma-separated list of admin identity IDs or Steam IDs. |
| **`GAME_MAX_PLAYERS`** | `32` | Maximum number of players allowed. |
| **`GAME_MODS_IDS_LIST`** | (empty) | Comma-separated list of mod IDs with optional versions. |
| **`GAME_MODS_JSON_FILE_PATH`** | (empty) | Path to a JSON file containing mod definitions. |
| **`GAME_NAME`** | `Arma Reforger Docker Server` | Name of the server. |
| **`GAME_PASSWORD`** | (empty) | Password to join the server. |
| **`GAME_PASSWORD_ADMIN`** | (empty) | Admin password for the server. Automatically generated if empty |
| **`GAME_PROPS_BATTLEYE`** | `true` | Whether BattlEye anti-cheat is enabled. |
| **`GAME_PROPS_DISABLE_THIRD_PERSON`** | `false` | Whether third-person view is disabled. |
| **`GAME_PROPS_FAST_VALIDATION`** | `true` | Whether fast validation is enabled. |
| **`GAME_PROPS_NETWORK_VIEW_DISTANCE`** | `1000` | Network view distance. |
| **`GAME_PROPS_SERVER_MAX_VIEW_DISTANCE`** | `2500` | Maximum view distance on the server. |
| **`GAME_PROPS_SERVER_MIN_GRASS_DISTANCE`** | `50` | Minimum grass rendering distance. |
| **`GAME_SCENARIO_ID`** | `{ECC61978EDCC2B5A}Missions/23_Campaign.conf` | Scenario to load on the server. |
| **`GAME_SUPPORTED_PLATFORMS`** | `PLATFORM_PC,PLATFORM_XBL,PLATFORM_PSN` | Platforms supported by the server. |
| **`GAME_VISIBLE`** | `true` | Whether the server is visible in the browser. |
| **`RCON_ADDRESS`** | `0.0.0.0` | Address for RCON. |
| **`RCON_PASSWORD`** | (empty) | Password for RCON (required to enable it). |
| **`RCON_PERMISSION`** | `admin` | Permission level for RCON clients. |
| **`RCON_PORT`** | `19999` | Port for RCON. |
| **`SERVER_A2S_ADDRESS`** | `0.0.0.0` | Address for A2S queries. |
| **`SERVER_A2S_PORT`** | `17777` | Port for A2S queries. |
| **`SERVER_BIND_ADDRESS`** | `0.0.0.0` | Address to bind the server to. |
| **`SERVER_BIND_PORT`** | `2001` | Port to bind the server to. |
| **`SERVER_PUBLIC_ADDRESS`** | (empty) | Public IP address of the server. |
| **`SERVER_PUBLIC_PORT`** | `2001` | Public port of the server. |
| **`SKIP_INSTALL`** | `false` | Whether to skip the installation of server files. |
| **`STEAM_APPID`** | `1874900` | Steam App ID. Use `1890870` for the experimental server. |
| **`STEAM_BRANCH`** | `public` | Steam branch to use (e.g., `public`, `beta`). |
| **`STEAM_BRANCH_PASSWORD`** | (empty) | Password for a private Steam branch. |
| **`STEAM_PASSWORD`** | (empty) | Steam password for the specified user. |
| **`STEAM_USER`** | (empty) | Steam username. Defaults to anonymous login. |

For a complete and up-to-date list of environment variables, check the `Dockerfile` as the source of truth.

---

## Custom Configuration File

To use a custom configuration file:

1. Start the server once to generate the default configuration file (`docker_generated.json`) in the `configs` directory.
2. Rename and modify this file as needed (e.g., `my_custom_config.json`).
3. Update the `ARMA_CONFIG` environment variable to point to the new file.
4. Restart the server to apply the changes.

---

## Example `.env` File

Here’s an example `.env` file for configuring your server:

```env
ARMA_CONFIG=docker_generated.json
GAME_NAME=My Custom Server
GAME_PASSWORD=
GAME_PASSWORD_ADMIN=ChangeMeNow!123
GAME_MAX_PLAYERS=64
GAME_SCENARIO_ID={3DAD390C31623F04}Missions/24_OVT_Eden.conf
SKIP_INSTALL=false
```

---

## Volumes and Data Persistence

To ensure server files and configurations persist across container restarts, map a host directory to `/reforger` in your Docker Compose or Docker run command:

```yaml
volumes:
    - ./reforger:/reforger
```

For more advanced configuration options, refer to the [Advanced Usage](../advanced-usage/index.md) section.

# Parameters

The following parameters can be set in your Docker configuration:

| Variable                             | Type    | Default Value                                  | Description |
|--------------------------------------|---------|------------------------------------------------|-------------|
| STEAM_USER                           | string  | ""                                             | User to use when downloading from Steamcmd            |
| STEAM_PASSWORD                       | string  | ""                                             | Password to user (required if changing `STEAM_USER`)            |
| STEAM_APPID                          | string  | "1874900"                                      | App ID to download from SteamCMD (`1874900` is Stable Branch, `1890870` is the Experimental Branch)            |
| STEAM_BRANCH                         | string  | "public"                                       | Choose which branch of Steam to use            |
| STEAM_BRANCH_PASSWORD                | string  | ""                                             | Some Steam branches may require a password, enter that here            |
| ARMA_CONFIG                          | string  | "docker_generated"                             | Name of the config file to use minus the extension, this will be relative to `/reforger/Configs` E.g: `my_server` would be `/reforger/Configs/my_server.json`. Note that setting this to a custom configuration will have many of these parameters overridden by values in the config file            |
| ARMA_PROFILE                         | string  | /home/profile                                  | Path to the Profile folder to use (inside the container)            |
| ARMA_BINARY                          | string  | "./ArmaReforgerServer"                         | Path to the Dedicated Server executable (inside the container)            |
| ARMA_PARAMS                          | string  | ""                                             | Pass various launch parameters here, they are separated as they would be if you were to run them locally on your machine            |
| ARMA_MAX_FPS                         | integer | 120                                            | Maximum FPS your server should run at (recommended to set this to either 60 or 120 FPS)            |
| ARMA_WORKSHOP_DIR                    | string  | "/reforger/workshop"                           | Path to the Workshop folder where mods will be downloaded and kept. Note that there is a volume tied to the default value.            |
| SERVER_BIND_ADDRESS                  | string  | "0.0.0.0"                                      | Bind address to use on your server            |
| SERVER_BIND_PORT                     | integer | 2001                                           | Bind port to use on your server (inside the container)            |
| SERVER_PUBLIC_ADDRESS                | string  | ""                                             | Public address to use on your server, leave blank to fetch automatically            |
| SERVER_PUBLIC_PORT                   | integer | 2001                                           | Public port to use on your server (inside the container)            |
| SERVER_A2S_ADDRESS                   | string  | "0.0.0.0"                                      | A2S address to use on your server            |
| SERVER_A2S_PORT                      | integer | 17777                                          | A2S port to use on your server            |
| RCON_ADDRESS                         | string  | "0.0.0.0"                                      | RCON address to use on your server            |
| RCON_PORT                            | integer | 19999                                          | RCON port to use on your server (inside the container)            |
| RCON_PASSWORD                        | string  | ""                                             | RCON password required for RCON clients to log in with            |
| RCON_PERMISSION                      | string  | "admin"                                        | RCON permission level (either `admin` or `monitor`)            |
| GAME_NAME                            | string  | "Arma Reforger Docker Server"                  | Name of your server that will appear in the server browser            |
| GAME_PASSWORD                        | string  | ""                                             | Password required to join the server, keeping this as default will have your server joinable by anyone            |
| GAME_PASSWORD_ADMIN                  | string  | ""                                             | Password for server administration in game, leaving this as default will have a random one generated on startup and printed to console            |
| GAME_ADMINS                          | string  | ""                                             | Comma separated list of STEAM64IDs representing players who will automatically become admins when logging into the server            |
| GAME_SCENARIO_ID                     | string  | "{ECC61978EDCC2B5A}Missions/23_Campaign.conf"  | Scenario ID to play on your server            |
| GAME_MAX_PLAYERS                     | integer | 32                                             | Max number of players            |
| GAME_VISIBLE                         | boolean | true                                           | Whether game is visible on the Server Browser. If set to false will require players use the direct connect function            |
| GAME_SUPPORTED_PLATFORMS             | string  | "PLATFORM_PC,PLATFORM_XBL"                     | Whether to use crossplay or not. `PLATFORM_PC` is required, you cannot host an Xbox only server            |
| GAME_PROPS_BATTLEYE                  | boolean | true                                           | Whether BattlEye anti-cheat is enabled            |
| GAME_PROPS_DISABLE_THIRD_PERSON      | boolean | false                                          | Disable Third Person perspective or not            |
| GAME_PROPS_FAST_VALIDATION           | boolean | true                                           | Validation of map entities and components loaded on client when it joins, ensuring things match with initial server state (recommend keeping as default)            |
| GAME_PROPS_SERVER_MAX_VIEW_DISTANCE  | integer | 2500                                           | Server-enforced Max View Distance            |
| GAME_PROPS_SERVER_MIN_GRASS_DISTANCE | integer | 50                                             | Server-enforced Min Grass Render Distance            |
| GAME_PROPS_NETWORK_VIEW_DISTANCE     | integer | 1000                                           | Maximum network streaming range of replicated entities            |
| GAME_MODS_IDS_LIST                   | string  | ""                                             | Comma separated list of mods to download and use, simple at the expense of not being as flexible / readable as `GAME_MODS_JSON_FILE_PATH` as you can't see what the mods are named or choose which version to use            |
| GAME_MODS_JSON_FILE_PATH             | string  | ""                                             | Alternative to `GAME_MODS_IDS_LIST`, JSON file containing all mods and versions to download and use            |

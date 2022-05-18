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
        -e STEAM_USER=username \
        -e STEAM_PASSWORD=password \
        -e SERVER_REGION="EU" \
        -e GAME_NAME=server_name \
        ghcr.io/brettmayson/arma-reforger:latest
```

The Steam account does not need to own Arma Reforger, but must have Steam Guard disabled.

If an admin password is not provided, one will be generated and printed to the console. It will be saved in the config and persist between restarts.

## Parameters

Check the dockerfile, more docs will come later.

### Configs

By default the configs are generated from the ENV variables in the dockerfile. After the first run the file can be expanded with additional options manually, but the fields will always be overwritten by the ENV variables.

Alternatively, change the `ARMA_CONFIG` variable to a file present in the `Configs` volume. It will be used without modification.

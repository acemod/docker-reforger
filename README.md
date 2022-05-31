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
        -e SERVER_REGION="EU" \
        -e SERVER_HOST_REGISTER_ADDRESS="public ip" \
        -e GAME_NAME="My Docker Reforger Server" \
        ghcr.io/acemod/arma-reforger:edge
```

If an admin password is not provided, one will be generated and printed to the console.

### Docker-compose

Simply check-out / copy [the provided docker-compose.yml](docker-compose.yml) and adjust to your personal needs.

## Parameters

Check [the Dockerfile](Dockerfile#L32-L67), more docs will come later.

### Configs

By default the configs are generated from the ENV variables in the dockerfile. After the first run the file can be expanded with additional options manually, but the fields will always be overwritten by the ENV variables.

Alternatively, change the `ARMA_CONFIG` variable to a file present in the `Configs` volume. It will be used without modification.

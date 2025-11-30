# Getting Started

This guide will walk you through deploying the Arma Reforger dedicated server using Docker.

## Prerequisites

- Docker installed and running on your system.
- Docker Compose (optional, but recommended).

## Deployment

### Docker CLI

1. Create the container:

    ```bash
    docker create \
      --name=reforger-server \
      -p 2001:2001/udp \
      -p 17777:17777/udp \
      ghcr.io/acemod/arma-reforger:latest
    ```

2. Start the container:

    ```bash
    docker start reforger-server
    ```

### Docker Compose

1. Create a `docker-compose.yml` file:

    ```yaml
    ---
    services:
      arma-reforger:
        image: ghcr.io/acemod/arma-reforger:latest
        ports:
          - "2001:2001/udp"
          - "17777:17777/udp"
        environment:
          - GAME_NAME="My Reforger Server"
    ```

2. Start the server:

    ```bash
    docker compose up -d
    ```

See the [Configuration Documentation](../configuration-guide/index.md) for available environment variables.

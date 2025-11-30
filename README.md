# Arma Reforger Dedicated Server

A lightweight and automated solution for running an Arma Reforger dedicated server. This project ensures your server is always up-to-date with the latest version.

## Quick Start

### Using Docker CLI

Run the following command to create and start the server:

```sh
docker create \
  --name=reforger-server \
  -p 2001:2001/udp \
  -v path/to/configs:/reforger/Configs \
  -v path/to/profiles:/home/profile \
  -v path/to/workshop:/reforger/workshop \
  -e SERVER_PUBLIC_ADDRESS="your.public.ip" \
  -e GAME_NAME="My Reforger Server" \
  ghcr.io/acemod/arma-reforger:latest
docker start reforger-server
```

> **Note**: If you don't provide an admin password, one will be generated and displayed in the console.

### Using Docker Compose

1. Clone the repository and navigate to the `docker-compose-examples` folder.
2. Choose a `docker-compose.yml` file that suits your needs and adjust it as necessary.
3. Start the server:

   ```bash
   docker compose up -d
   ```

4. Stop the server:

   ```bash
   docker compose down
   ```

## Learn More

For detailed configuration options, advanced usage, and troubleshooting, refer to the [documentation](docs/index.md).

- **Environment Variables**: Customize your server with a wide range of options.
- **Mods Support**: Add mods using environment variables or JSON files.
- **Multiple Instances**: Run multiple servers on the same machine.
- **RCON**: Enable and configure remote server control.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests to improve the project.

---

Get started today and enjoy a seamless Arma Reforger server experience!

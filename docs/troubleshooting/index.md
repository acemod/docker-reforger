# Troubleshooting

This section provides solutions to common issues encountered when running the Arma Reforger Dedicated Server with Docker.

---

## [Errno 2] No such file or directory: './ArmaReforgerServer'

**Problem:**  
The server fails to start because the `ArmaReforgerServer` binary is missing. This typically occurs if the server files have not been installed or if the installation directory is not persisted.

**Solution:**  

1. Ensure that `SKIP_INSTALL` is set to `false` during the first run to download the server files.
2. Use a persistent Docker volume for `/reforger` to retain the server files across restarts.
3. If `SKIP_INSTALL=true` is set, verify that the binary exists in the mounted volume.

---

## Docker Volume Issues

**Problem:**  
Server files are lost after stopping or removing the container.

**Solution:**  

- Always map a persistent volume from the host to `/reforger` in your Docker or Docker Compose configuration.
- Example for Docker Compose:

    ```yaml
    volumes:
        - ./reforger:/reforger
    ```

---

## RCON Not Working

**Problem:**
RCON does not connect or fails to authenticate.

**Solution:**

1. Ensure `RCON_PASSWORD` is set and meets the requirements (at least 3 characters, no spaces).
2. Verify that the RCON port is correctly mapped and not blocked by a firewall.

---

## Configuration Not Applied

**Problem:**
Changes to environment variables do not reflect in the server.

**Solution:**

1. If you are using a custom configuration file (not `docker_generated.json`), ensure the `ARMA_CONFIG` environment variable is set to the path of your file. Double-check that the file contains the desired configuration settings.
2. Restart the container after making changes to environment variables or configuration files.
3. If the issue persists, verify that the configuration file is correctly formatted and accessible by the container.
4. Alternatively, edit the file directly in the mounted volume to ensure changes are applied.

---

## Need More Help?

- Refer to the [Documentation](../index.md) for setup and configuration examples.
- Consult the [Configuration Guide](../configuration-guide/index.md) for detailed information on environment variables.
- Explore the [Advanced Usage](../advanced-usage/index.md) section for complex scenarios.

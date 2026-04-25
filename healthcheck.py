"""Simple A2S_INFO health check for Arma Reforger server.

Uses the active server configuration when available, falls back to the A2S
environment variables before the generated config exists, and treats disabled
A2S as a no-op so valid configurations are not marked unhealthy.
"""

import json
import os
import socket
import sys
from pathlib import Path

A2S_INFO_REQUEST = b"\xFF\xFF\xFF\xFF\x54Source Engine Query\x00"
CONFIG_GENERATED = Path("/reforger/Configs/docker_generated.json")
CONFIG_DIR = Path("/reforger/Configs")
TIMEOUT_SECONDS = 5
WILDCARD_TO_LOOPBACK = {
    "": "127.0.0.1",
    "0.0.0.0": "127.0.0.1",
    "::": "::1",
}


def resolve_config_path():
    arma_config = os.environ.get("ARMA_CONFIG", "docker_generated")
    if arma_config == "docker_generated":
        return CONFIG_GENERATED
    return CONFIG_DIR / arma_config


def resolve_a2s_settings():
    config_path = resolve_config_path()
    if config_path.exists():
        with config_path.open() as f:
            config = json.load(f)
        return config.get("a2s")

    address = os.environ.get("SERVER_A2S_ADDRESS", "")
    port = os.environ.get("SERVER_A2S_PORT", "")
    if not address or not port:
        return None
    return {"address": address, "port": int(port)}


def probe_server(address, port):
    probe_address = WILDCARD_TO_LOOPBACK.get(address, address)
    addrinfos = socket.getaddrinfo(probe_address, port, type=socket.SOCK_DGRAM)
    for family, socktype, proto, _, sockaddr in addrinfos:
        sock = socket.socket(family, socktype, proto)
        try:
            sock.settimeout(TIMEOUT_SECONDS)
            sock.sendto(A2S_INFO_REQUEST, sockaddr)
            data, _ = sock.recvfrom(4096)
            if data:
                return True
        except OSError:
            continue
        finally:
            sock.close()
    return False


try:
    a2s = resolve_a2s_settings()
    if not a2s:
        sys.exit(0)
    sys.exit(0 if probe_server(a2s["address"], a2s["port"]) else 1)
except Exception:
    sys.exit(1)

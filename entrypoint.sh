#!/bin/bash
set -e

# Fix ownership of mounted volumes so the non-root user can write to them
chown -R reforger:reforger /reforger /steamcmd /home/profile 2>/dev/null || true

# Drop to non-root user and exec the launch script
exec gosu reforger:reforger python3 /launch.py

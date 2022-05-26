import sys
import time

import a2s

SERVER_ADDRESS = ("127.0.0.1", 17777)

ATTEMPTS = 250
SLEEP = 0.5

print("Looking for server (will try {} attempts)...".format(ATTEMPTS))
while ATTEMPTS > 0:
    try:
        info = a2s.info(SERVER_ADDRESS)
        print("Server found")
        print("Game: " + info.game)
        print("Map: " + info.map_name)
        print("Version: " + info.version)
        sys.exit(0)
    except Exception as e:
        print(e)
        ATTEMPTS -= 1
        time.sleep(SLEEP)

print("Server not found")
sys.exit(1)

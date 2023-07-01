#!/usr/bin/env python3
import os, sys, socket
host = sys.argv[1]
if len(sys.argv) > 2:
    ports = sys.argv[2:]
else:
    ports = os.getenv("KNOCK_PORTS", "").split(",")
for port in ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setblocking(True)
    s.settimeout(0.01)
    try:
        s.connect((host, int(port)))
        s.send(b"\0")
    except (socket.timeout, ConnectionRefusedError):
        continue
    else:
        print(f"Port {port} open!", file=sys.stderr)
        #raise Exception(f"Port {port} not closed!")
    finally:
        s.close()


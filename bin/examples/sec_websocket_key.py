#!/usr/bin/env python3
import sys
from hashlib import sha1
from base64 import b64encode, b64decode
uuid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

if "-h" in sys.argv:
    sys.exit("USAGE: {} KEY".format(sys.argv[0]))
if len(sys.argv) == 2:
    key = sys.argv[1]
else:
    key = sys.stdin.read().strip()

target = key + uuid
hashed = sha1(target.encode("utf-8")).digest()
encoded = b64encode(hashed).decode("utf-8")
print(encoded)

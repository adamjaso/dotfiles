#!/usr/bin/env python3
import json
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
while True:
    packet, _, _, src = sock.recvmsg(65535)
    packet = [("%02x" % c) for c in packet]
    ipheader = packet[:20]
    ippayload = packet[20:]
    print(json.dumps([src, " ".join(ipheader), " ".join(ippayload)]))

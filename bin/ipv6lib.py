#!/usr/bin/env python3
import argparse
import socket
import struct
import urllib
from urllib import request


def getipv6_attr(attr):
    url = f"http://169.254.169.254/metadata/v1/interfaces/public/0/ipv6/{attr}"
    req = request.Request(url)
    res = request.urlopen(req, timeout=0.2)
    return res.read().decode("utf-8")


def ipv6_to_int(addr):
    addr_bytes = socket.inet_pton(socket.AF_INET6, addr)
    a, b = struct.unpack(">QQ", addr_bytes)
    return (a << 64) | b


def int_to_ipv6(addr_int):
    a = addr_int >> 64
    b = addr_int & ((1 << 64) - 1)
    addr_bytes = struct.pack(">QQ", a, b)
    return socket.inet_ntop(socket.AF_INET6, addr_bytes)


def split_cidr(cidr, default_mask=128):
    if "/" in cidr:
        addr, bits = cidr.split("/", 1)
        return addr, int(bits)
    else:
        return cidr, default_mask


def ipv6_calc(
    ipv6addr,
    addr_mask=128,
    next_net=False,
    addr_network=False,
    addr_gateway=False,
    addr_broadcast=False,
    addr_add=0,
    addr_sub=0,
    with_mask=False,
):
    addr, addr_mask = split_cidr(ipv6addr, default_mask=addr_mask)

    addr_int = ipv6_to_int(addr)
    mask_ones = ((1 << addr_mask) - 1) << (128 - addr_mask)
    mask_size = 1 << (128 - addr_mask)

    if next_net or addr_network or addr_gateway or addr_broadcast:
        addr_int &= mask_ones

    if next_net:
        addr_int += next_net * mask_size

    if addr_gateway:
        addr_int += 1
    elif addr_broadcast:
        addr_int += mask_size - 1

    if addr_add:
        addr_int += addr_add
    elif addr_sub:
        addr_int -= addr_sub

    addr_str = int_to_ipv6(addr_int)
    if with_mask and addr_mask:
        addr_str += "/" + str(addr_mask)
    return addr_str


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ipv6addr", nargs="?")
    parser.add_argument("-m", "--mask", type=int, default=128)
    parser.add_argument("--next", type=int, default=0)
    parser.add_argument("--with-mask", action="store_true")
    gb = parser.add_mutually_exclusive_group()
    gb.add_argument("-N", "--network", action="store_true")
    gb.add_argument("-G", "--gateway", action="store_true")
    gb.add_argument("-B", "--broadcast", action="store_true")
    g = parser.add_mutually_exclusive_group()
    g.add_argument("-a", "--add", type=int, default=0)
    g.add_argument("-s", "--sub", type=int, default=0)
    args = parser.parse_args()

    try:
        ipv6addr = args.ipv6addr or getipv6_attr("address")
    except urllib.error.URLError:
        parser.print_help()
        return

    addr_str = ipv6_calc(
        ipv6addr,
        addr_mask=args.mask,
        next_net=args.next,
        addr_network=args.network,
        addr_gateway=args.gateway,
        addr_broadcast=args.broadcast,
        addr_add=args.add,
        addr_sub=args.sub,
        with_mask=args.with_mask,
    )
    print(addr_str)


if __name__ == "__main__":
    main()

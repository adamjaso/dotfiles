#!/usr/bin/env python3
import argparse

parser = argparse.ArgumentParser()
g = parser.add_mutually_exclusive_group(required=True)
g.add_argument("-x", "--hex")
g.add_argument("-r", "--rgb", nargs=3)
parser.add_argument("-b", "--base", type=int, default=10)
parser.add_argument("--invert", action="store_true")
args = parser.parse_args()

rgb = args.rgb if args.rgb else range(0, 6, 2)
if args.hex:
    color = args.hex.lstrip("#")
    rgb = tuple(int(color[i : i + 2], 16) for i in rgb)
else:
    rgb = tuple(int(i, args.base) for i in args.rgb)
if args.invert:
    rgb = tuple(0xFF - i for i in rgb)
print("#%02x%02x%02x" % rgb)

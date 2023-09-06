#!/usr/bin/env python3
import re
import sys
import json
from collections import defaultdict

alldeps = defaultdict(set)
for line in sys.stdin:
    parts = re.split("\s+", line.strip(), maxsplit=2)
    if len(parts) != 2:
        print("invalid entry", parts, file=sys.stderr)
        continue
    alldeps[parts[0]].add(parts[1])


def build_tree(children):
    childdeps = {}
    for child in children:
        if child in alldeps:
            childdeps[child] = build_tree(alldeps[child])
        else:
            childdeps[child] = None
    return childdeps


tree = {}
for parent, children in alldeps.items():
    tree[parent] = build_tree(children)

if len(sys.argv) > 1:
    json.dump({child: tree[child] for child in sys.argv[1:]}, sys.stdout, indent=2)
else:
    json.dump(tree, sys.stdout, indent=2)

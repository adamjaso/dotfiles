#!/usr/bin/env python3
#
# Go list dependencies:
#
#  Several ways to inspect the tree of Golang go.mod dependencies.
#  List dependencies using `go list`
#  ```
#  go list -f '{{ range .Deps }}{{$.ImportPath}} {{.}}'$'\n''{{end}}'
#  ```
#  Read output of `go list` above and print the tree as json.

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


cache = {}


def build_tree(children, c):
    childdeps = {}
    for child in children:
        print(' '*c, child, file=sys.stderr)
        if child in alldeps:
            childdeps[child] = build_tree(alldeps[child], c+1)
        else:
            childdeps[child] = None
    return childdeps


tree = {}
for parent, children in alldeps.items():
    tree[parent] = build_tree(children, 1)

if len(sys.argv) > 1:
    json.dump({child: tree[child] for child in sys.argv[1:]}, sys.stdout, indent=2, default=str)
else:
    json.dump(tree, sys.stdout, indent=2)

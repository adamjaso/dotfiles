#!/usr/bin/env python3
import re
import sys
import json
import argparse


def get_full_tree(pid, parentchild, cmds):
    res = {"pid": pid}
    if pid in cmds:
        res["cmd"] = cmds[pid]
    if pid not in parentchild:
        return res
    res["child"] = {}
    for child in parentchild[pid]:
        res["child"][child] = get_full_tree(child, parentchild, cmds)
    return res


def get_minimal_tree(pid, parentchild, cmds):
    if pid not in parentchild:
        return cmds[pid]
    res = {}
    for child in parentchild[pid]:
        res[child] = get_minimal_tree(child, parentchild, cmds)
    return res


def main():
    args = argparse.ArgumentParser()
    args.add_argument("-p", "--pid", default="0")
    args.add_argument("--full", action="store_true")
    args.add_argument("--digits-only", action="store_true")
    args = args.parse_args()

    lines = [line.strip() for line in sys.stdin]
    cmds = {}
    parentchild = {}
    for line in lines:
        pid, ppid, cmd = re.split("\s+", line, 2)
        cmds[pid] = cmd
        if ppid not in parentchild:
            parentchild[ppid] = []
        parentchild[ppid].append(pid)

    if args.digits_only:
        tree = parentchild
    elif args.full:
        tree = get_full_tree(args.pid, parentchild, cmds)
    else:
        tree = get_minimal_tree(args.pid, parentchild, cmds)
    json.dump(tree, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import sys
import json
import argparse

def linregress(xs, ys):
    n = len(xs)
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum([xs[i] * ys[i] for i in range(n)])
    sum_x2 = sum([x * x for x in xs])
    sum_y2 = sum([y * y for y in ys])
    denom = n * sum_x2 - sum_x**2
    if denom == 0:
        return 0, 0
    b = (n * sum_xy - sum_x * sum_y) / denom
    a = (sum_y * sum_x2 - sum_x * sum_xy) / denom
    rsq_numer = (n * sum_xy - sum_x * sum_y)**2
    rsq_denom = (n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2)
    rsq = rsq_numer / rsq_denom
    return a, b, rsq


def parse_series(line):
    pairs = [pair.split(',') for pair in line.strip().split('|')]
    xs = [float(pair[0]) for pair in pairs]
    ys = [float(pair[1]) for pair in pairs]
    return xs, ys


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--intercept-slope', dest='ab', action='store_true')
    args.add_argument('--interval-stats', action='store_true')
    args.add_argument('--summary', action='store_true')
    args = args.parse_args()

    n = 0
    total = 0.0
    b_total = 0.0
    for line in sys.stdin:
        n += 1
        xs, ys = parse_series(line)
        try:
            a, b, _ = linregress(xs, ys)
            total += xs[-1] - xs[0]
            b_total += b
            if args.ab:
                print(a, b)  # y = a + b * x
            elif args.interval_stats:
                print(xs[-1] - xs[0], 's', b/1024**2, 'M/s')
        except ZeroDivisionError:
            pass
    if args.summary:
        if n > 0:
            print(total, n, total / n, 's', b_total / 1024**2 / n, 'M/s')
        else:
            print(0, 0, 0, 's')


if __name__ == '__main__':
    main()

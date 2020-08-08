#!/usr/bin/env python3
import sys
import time
import signal
import argparse
import subprocess
from urllib import parse


def main():
    args = argparse.ArgumentParser(
        description="psqlssh: SSH port forward through a bastion host to a "
        "Postgres server and connect to that Postgres server using the 'psql' "
        "tool"
    )
    args.add_argument(
        "bastion_host",
        help="The bastion host. This can be a name in your ~/.ssh/config",
    )
    args.add_argument(
        "psql_url",
        help="The postgres server URL. It expects the format of "
        "'postgres://$USER:$PASS@$HOSTNAME:$PORT/$DBNAME'.",
    )
    args.add_argument(
        "--local-port",
        type=int,
        default=5433,
        help="The port to bind on your local system",
    )
    args.add_argument(
        "--local-host",
        default="localhost",
        help="The address to bind on your local system",
    )
    args.add_argument(
        "--remote-port",
        type=int,
        default=5432,
        help="The remote Postgres port to connect to. This is only used when "
        "no port is set in PSQL_URL.",
    )
    args.add_argument(
        "--wait-seconds",
        type=int,
        default=4,
        help="This indicates how long to wait for the SSH port forwarding to "
        "connect.",
    )
    args.add_argument(
        "--dump",
        action="store_true",
        help="This indicates to dump the Postgres database using 'pg_dump'",
    )
    args = args.parse_args()

    sshp = ssh_port_forward(
        args.psql_url, args.bastion_host, args.local_port, args.remote_port,
    )
    signal.signal(signal.SIGINT, lambda *args: None)
    time.sleep(args.wait_seconds)
    psqlp = psql_command(
        args.psql_url, args.local_host, args.local_port, dump=args.dump,
    )
    try:
        if psqlp.wait() != 0:
            print("psql error occurred", file=sys.stderr)
    finally:
        sshp.terminate()


def psql_command(psql_url, local_host, local_port, dump=False):
    psql = parse.urlsplit(psql_url)
    psql_url = parse.urlunsplit(
        (
            psql.scheme,
            f"{psql.username}:{psql.password}@{local_host}:{local_port}",
            psql.path,
            psql.query,
            "",
        )
    )
    if dump:
        psql_command = ["pg_dump", "--data-only", psql_url]
    else:
        psql_command = ["psql", psql_url]
    print(*psql_command, file=sys.stderr)
    return subprocess.Popen(psql_command)


def ssh_port_forward(psql_url, bastion_host, local_port, remote_port):
    psql = parse.urlsplit(psql_url)
    remote_host = psql.hostname
    remote_port = str(psql.port or remote_port)
    forward_host = ":".join([str(local_port), remote_host, remote_port])
    ssh_port_forward = [
        "ssh",
        "-NL",
        forward_host,
        bastion_host,
    ]
    print(*ssh_port_forward, file=sys.stderr)
    return subprocess.Popen(ssh_port_forward)


if __name__ == "__main__":
    main()

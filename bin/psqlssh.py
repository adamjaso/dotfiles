#!/usr/bin/env python3
import os
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
    args.add_argument(
        "--backup",
        action="store_true",
        help="Dump the database in the custom 'pg_dump' binary format (-Fc).",
    )
    args.add_argument(
        "--column-inserts",
        action="store_true",
        help="This indicates to use pg_dump with the '--column-inserts' flag",
    )
    args.add_argument(
        "--schema-only",
        action="store_true",
        help="This indicates to use 'pg_dump' to dump the Postgres database schema only",
    )
    args.add_argument(
        "--run-query",
        help="This indicates to use 'psql' to execute the given query and output the result as a CSV i.e. psql -c QUERY --csv",
    )
    args.add_argument(
        "-t",
        "--include-tables",
        nargs="*",
        help="This indicates to specify for 'pg_dump' to include the given table names.",
    )
    args.add_argument(
        "-T",
        "--exclude-tables",
        nargs="*",
        help="This indicates to specify for 'pg_dump' to exclude the given table names.",
    )
    args.add_argument(
        "--use-history",
        action="store_true",
        help="This indicates to allow PSQL_HISTORY; default is to ignore PSQL_HISTORY",
    )
    args = args.parse_args()

    def signal_handler(*args):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    signal_handler()

    sshp = ssh_port_forward(
        args.psql_url,
        args.bastion_host,
        args.local_port,
        args.remote_port,
    )
    time.sleep(args.wait_seconds)
    psqlp = psql_command(
        args.psql_url,
        args.local_host,
        args.local_port,
        dump=args.dump,
        backup=args.backup,
        column_inserts=args.column_inserts,
        schema_only=args.schema_only,
        exclude_tables=args.exclude_tables,
        include_tables=args.include_tables,
        use_history=args.use_history,
        run_query=args.run_query,
    )
    try:
        if psqlp.wait() != 0:
            print("psql error occurred", file=sys.stderr)
    finally:
        sshp.terminate()


def psql_command(
    psql_url,
    local_host,
    local_port,
    dump=False,
    schema_only=False,
    column_inserts=False,
    exclude_tables=None,
    include_tables=None,
    backup=False,
    use_history=False,
    run_query=None,
):
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
        if schema_only:
            psql_command = [
                "pg_dump",
                "--schema-only",
                "--no-owner",
                "--no-acl",
                psql_url,
            ]
        else:
            psql_command = [
                "pg_dump",
                "--data-only",
                "--no-owner",
                "--no-acl",
                psql_url,
            ]
            if backup:
                psql_command.insert(1, "-Fc")
            elif column_inserts:
                psql_command.insert(1, "--column-inserts")
            else:
                psql_command.insert(1, "--on-conflict-do-nothing")
                psql_command.insert(1, "--inserts")
            if exclude_tables or include_tables:
                tables_flags = []
                if exclude_tables:
                    for table_name in exclude_tables:
                        tables_flags += ["-T", table_name]
                if include_tables:
                    for table_name in include_tables:
                        tables_flags += ["-t", table_name]
                psql_command = psql_command[0:1] + tables_flags + psql_command[1:]
            print(psql_command, file=sys.stderr)
    else:
        psql_command = ["psql", psql_url]
        if run_query:
            psql_command.extend(["-c", run_query, "--csv"])
    env = {name: value for name, value in os.environ.items()}
    if not use_history:
        env["PSQL_HISTORY"] = os.devnull
    return subprocess.Popen(psql_command, env=env)


def ssh_port_forward(psql_url, bastion_host, local_port, remote_port):
    psql = parse.urlsplit(psql_url)
    remote_host = psql.hostname
    remote_port = psql.port or remote_port
    ssh_port_forward = [
        "ssh",
        "-qNL",
        f"{local_port}:{remote_host}:{remote_port}",
        bastion_host,
    ]
    return subprocess.Popen(ssh_port_forward)


if __name__ == "__main__":
    main()

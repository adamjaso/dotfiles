#!/usr/bin/env python3
import os
import sys
import time
import shlex
import signal
import argparse
import subprocess
from urllib import parse


def main():
    parser = argparse.ArgumentParser(
        description="psqlssh: SSH port forward through a bastion host to a "
        "Postgres server and connect to that Postgres server using the 'psql' "
        "tool"
    )
    parser.add_argument(
        "--ssh-verbose",
        action="store_true",
        help="Add -v to the ssh port-forward",
    )
    parser.add_argument("--ssh-config", help="Add -F to the ssh port forward")
    parser.add_argument(
        "--local-host",
        default="localhost",
        help="The address to bind on your local system",
    )
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=4,
        help="This indicates how long to wait for the SSH port forwarding to "
        "connect.",
    )
    parser.add_argument(
        "--show-commands",
        action="store_true",
        help="Dry run the command to show the ssh and psql/redis commands that would be run",
    )
    sps = parser.add_subparsers(dest="action")
    redis_args = sps.add_parser("redis")
    redis_args.add_argument(
        "bastion_host",
        help="The bastion host. This can be a name in your ~/.ssh/config",
    )
    redis_args.add_argument(
        "destination_url",
        help="The redis server URL. It expects the format of 'redis://:$PASS@$HOSTNAME:$PORT'.",
    )
    redis_args.add_argument(
        "--local-port",
        type=int,
        default=6380,
        help="The port to bind on your local system",
    )
    redis_args.add_argument(
        "--remote-port",
        type=int,
        default=6379,
        help="The remote Redis port to connect to. This is only used when "
        "no port is set in DESTINATION_URL.",
    )
    redis_args.add_argument(
        "--run-query",
        nargs="*",
        default=None,
        help="Run this Redis command instead of an interactive session.",
    )
    psql_args = sps.add_parser("psql")
    psql_args.add_argument(
        "bastion_host",
        help="The bastion host. This can be a name in your ~/.ssh/config",
    )
    psql_args.add_argument(
        "destination_url",
        help="The postgres server URL. It expects the format of "
        "'postgres://$USER:$PASS@$HOSTNAME:$PORT/$DBNAME'.",
    )
    psql_args.add_argument(
        "--psql-password",
        default=None,
        help="Postgres password to URL encode. Overrides the URL password, if present.",
    )
    psql_args.add_argument(
        "--psql-timeout",
        type=int,
        default=5,
        help="Postgres PGCONNECT_TIMEOUT value to set in seconds (set 0 to omit this setting)",
    )
    psql_args.add_argument(
        "--local-port",
        type=int,
        default=5433,
        help="The port to bind on your local system",
    )
    psql_args.add_argument(
        "--remote-port",
        type=int,
        default=5432,
        help="The remote Postgres port to connect to. This is only used when "
        "no port is set in DESTINATION_URL.",
    )
    psql_args.add_argument(
        "--dump",
        action="store_true",
        help="This indicates to dump the Postgres database using 'pg_dump'",
    )
    psql_args.add_argument(
        "--backup",
        action="store_true",
        help="Dump the database in the custom 'pg_dump' binary format (-Fc).",
    )
    psql_args.add_argument(
        "--column-inserts",
        action="store_true",
        help="This indicates to use pg_dump with the '--column-inserts' flag",
    )
    psql_args.add_argument(
        "--schema-only",
        action="store_true",
        help="This indicates to use 'pg_dump' to dump the Postgres database schema only",
    )
    psql_args.add_argument(
        "--run-query",
        help="This indicates to use 'psql' to execute the given query and output the result as a CSV i.e. psql -c QUERY --csv",
    )
    psql_args.add_argument(
        "-t",
        "--include-tables",
        nargs="*",
        help="This indicates to specify for 'pg_dump' to include the given table names.",
    )
    psql_args.add_argument(
        "-T",
        "--exclude-tables",
        nargs="*",
        help="This indicates to specify for 'pg_dump' to exclude the given table names.",
    )
    psql_args.add_argument(
        "--use-history",
        action="store_true",
        help="This indicates to allow PSQL_HISTORY; default is to ignore PSQL_HISTORY",
    )
    psql_args.add_argument(
        "--use-pager",
        action="store_true",
        help="This indicates to allow psql to use the built-in paging feature. Default dumps to stdout without paging. ",
    )
    args = parser.parse_args()

    def signal_handler(*args):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    signal_handler()

    sshp = ssh_port_forward(
        args.destination_url,
        args.bastion_host,
        args.local_port,
        args.remote_port,
        args.ssh_verbose,
        args.ssh_config,
        show_commands=args.show_commands,
    )
    if not args.show_commands:
        time.sleep(args.wait_seconds)
    if args.action == "psql":
        p = psql_command(
            args.destination_url,
            args.local_host,
            args.local_port,
            show_commands=args.show_commands,
            psql_password=args.psql_password,
            psql_timeout=args.psql_timeout,
            dump=args.dump,
            backup=args.backup,
            column_inserts=args.column_inserts,
            schema_only=args.schema_only,
            exclude_tables=args.exclude_tables,
            include_tables=args.include_tables,
            use_history=args.use_history,
            use_pager=args.use_pager,
            run_query=args.run_query,
        )
    elif args.action == "redis":
        p = redis_command(
            args.destination_url,
            args.local_host,
            args.local_port,
            run_query=args.run_query,
            show_commands=args.show_commands,
    )
    if args.show_commands:
        return
    try:
        if p.wait() != 0:
            print("psql error occurred", file=sys.stderr)
    finally:
        sshp.terminate()


def psql_command(
    psql_url,
    local_host,
    local_port,
    show_commands=False,
    psql_password=None,
    psql_timeout=None,
    dump=False,
    schema_only=False,
    column_inserts=False,
    exclude_tables=None,
    include_tables=None,
    backup=False,
    use_history=False,
    use_pager=False,
    run_query=None,
):
    psql = parse.urlsplit(psql_url)
    if not psql_password:
        psql_password = psql.password
    else:
        psql_password = parse.quote(psql_password, safe="")
    psql_url = parse.urlunsplit(
        (
            psql.scheme,
            f"{psql.username}:{psql_password}@{local_host}:{local_port}",
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
            # print(psql_command, file=sys.stderr)
    else:
        psql_command = ["psql", psql_url]
        if not use_pager:
            psql_command.extend(["-P", "pager=off"])
        if run_query:
            psql_command.extend(["-c", run_query, "--csv"])
    psql_env = {}
    if psql_timeout:
        psql_env["PGCONNECT_TIMEOUT"] = str(psql_timeout)
    if not use_history:
        psql_env["PSQL_HISTORY"] = os.devnull
    if show_commands:
        command = ["env"]
        command.extend([name+"="+shlex.quote(value) for name, value in psql_env.items()])
        command.extend([shlex.quote(value) for value in psql_command])
        print(" ".join(command))
        return None
    else:
        print(psql_command, file=sys.stderr)
    env = {name: value for name, value in os.environ.items()}
    env.update(psql_env)
    return subprocess.Popen(psql_command, env=env, stdin=sys.stdin)


def redis_command(
    redis_url,
    local_host,
    local_port,
    show_commands=False,
    run_query=None,
):
    redis = parse.urlsplit(redis_url)
    redis_cli = [
        "redis-cli",
        "-h",
        local_host,
        "-p",
        str(local_port),
    ]
    if run_query is not None:
        redis_cli.extend(run_query)
    redis_env = {"REDISCLI_AUTH": redis.password}
    if show_commands:
        command = ["env"]
        command.extend([name+"="+shlex.quote(value) for name, value in redis_env.items()])
        command.extend([shlex.quote(value) for value in redis_cli])
        print(" ".join(command))
        return None
    else:
        print(redis_cli, file=sys.stderr)
    return subprocess.Popen(redis_cli, env=redis_env)


def ssh_port_forward(
    psql_url,
    bastion_host,
    local_port,
    remote_port,
    ssh_verbose,
    ssh_config,
    show_commands=False,
):
    psql = parse.urlsplit(psql_url)
    remote_host = psql.hostname
    remote_port = psql.port or remote_port
    ssh_port_forward = [
        "ssh",
        "-NL",
        f"{local_port}:{remote_host}:{remote_port}",
        bastion_host,
    ]
    if ssh_verbose:
        ssh_port_forward.insert(1, "-v")
    else:
        ssh_port_forward.insert(1, "-q")
    if ssh_config:
        ssh_port_forward.insert(1, "-F" + ssh_config)
    if show_commands:
        print(" ".join(ssh_port_forward))
        return None
    else:
        print(ssh_port_forward, file=sys.stderr)
    return subprocess.Popen(ssh_port_forward)


if __name__ == "__main__":
    main()

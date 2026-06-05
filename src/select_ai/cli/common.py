# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import getpass
import os
import sys
from typing import Iterable, Optional

import click

import select_ai


def env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value if value else None


def connection_options(func):
    options = [
        click.option(
            "--wallet-password",
            default=env("SELECT_AI_WALLET_PASSWORD"),
            help="Wallet password. Defaults to SELECT_AI_WALLET_PASSWORD.",
        ),
        click.option(
            "--wallet-location",
            default=env("SELECT_AI_WALLET_LOCATION"),
            help="Wallet location. Defaults to SELECT_AI_WALLET_LOCATION.",
        ),
        click.option(
            "--dsn",
            default=env("SELECT_AI_DB_CONNECT_STRING"),
            help=(
                "Database connect string. Defaults to "
                "SELECT_AI_DB_CONNECT_STRING."
            ),
        ),
        click.option(
            "--password",
            default=env("SELECT_AI_PASSWORD"),
            help="Database password. Defaults to SELECT_AI_PASSWORD.",
        ),
        click.option(
            "--user",
            default=env("SELECT_AI_USER"),
            help="Database user. Defaults to SELECT_AI_USER.",
        ),
    ]
    for option in options:
        func = option(func)
    return func


def connect(
    user: Optional[str],
    password: Optional[str],
    dsn: Optional[str],
    wallet_location: Optional[str],
    wallet_password: Optional[str],
) -> None:
    missing = []
    if user is None:
        missing.append("--user or SELECT_AI_USER")
    if dsn is None:
        missing.append("--dsn or SELECT_AI_DB_CONNECT_STRING")
    if missing:
        raise click.ClickException(
            "Missing required connection values: " + ", ".join(missing)
        )
    if password is None:
        password = getpass.getpass("Database password: ")

    connect_args = {
        "user": user,
        "password": password,
        "dsn": dsn,
    }
    if wallet_location:
        connect_args["wallet_location"] = wallet_location
        connect_args["config_dir"] = wallet_location
    if wallet_password:
        connect_args["wallet_password"] = wallet_password
    select_ai.connect(**connect_args)


def profile(profile_name: str) -> select_ai.Profile:
    return select_ai.Profile(profile_name=profile_name)


def echo_command(command: str, description: str) -> None:
    click.echo(
        f"  {click.style(command, fg='green')}   "
        f"{click.style(description, fg='bright_black')}"
    )


def echo_profile(profile_name: str) -> None:
    click.echo(click.style(profile_name, fg="cyan"))


def echo_status(message: str) -> None:
    click.secho(message, fg="cyan")


def print_chunks(chunks: Iterable[str], color: Optional[str] = None) -> None:
    for chunk in chunks:
        if color:
            click.echo(click.style(chunk, fg=color), nl=False)
        else:
            sys.stdout.write(chunk)
            sys.stdout.flush()
    click.echo()
    sys.stdout.flush()


def print_text_result(result: object) -> None:
    if result is not None:
        click.echo(result)

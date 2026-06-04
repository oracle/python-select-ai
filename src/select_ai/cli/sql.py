# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import click

import select_ai
from select_ai.cli.common import (
    connect,
    connection_options,
    print_chunks,
    print_text_result,
    profile,
)


def _text_action(action):
    @click.command()
    @click.option(
        "--profile",
        "profile_name",
        required=True,
        help="Select AI profile name.",
    )
    @connection_options
    @click.option(
        "--no-stream",
        is_flag=True,
        help="Print the response after it is fully generated.",
    )
    @click.option(
        "--chunk-size",
        default=8192,
        show_default=True,
        help="Number of characters to read per streaming chunk.",
    )
    @click.argument("prompt")
    def command(
        profile_name,
        user,
        password,
        dsn,
        wallet_location,
        wallet_password,
        no_stream,
        chunk_size,
        prompt,
    ):
        connect(user, password, dsn, wallet_location, wallet_password)
        try:
            prof = profile(profile_name)
            method = getattr(prof, action)
            if no_stream:
                print_text_result(method(prompt))
            else:
                print_chunks(
                    method(prompt, stream=True, chunk_size=chunk_size)
                )
        finally:
            select_ai.disconnect()

    return command


@click.group()
def sql():
    """Generate, run, explain, and narrate SQL from natural language."""


@sql.command("run")
@click.option(
    "--profile",
    "profile_name",
    required=True,
    help="Select AI profile name.",
)
@connection_options
@click.argument("prompt")
def run_sql(
    profile_name,
    user,
    password,
    dsn,
    wallet_location,
    wallet_password,
    prompt,
):
    """Generate SQL, run it, and print the result table."""
    connect(user, password, dsn, wallet_location, wallet_password)
    try:
        result = profile(profile_name).run_sql(prompt)
        click.echo(result.to_string(index=False))
    finally:
        select_ai.disconnect()


sql.add_command(_text_action("show_sql"), "show")
sql.add_command(_text_action("explain_sql"), "explain")
sql.add_command(_text_action("narrate"), "narrate")

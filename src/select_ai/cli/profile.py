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
    echo_profile,
    print_text_result,
    profile,
)


@click.group()
def profile_group():
    """Run one-shot Select AI profile operations."""


@profile_group.command("list")
@connection_options
@click.option(
    "--pattern",
    default=".*",
    show_default=True,
    help="Regular expression used to match profile names.",
)
def list_profiles(
    user,
    password,
    dsn,
    wallet_location,
    wallet_password,
    pattern,
):
    """List Select AI profile names."""
    connect(user, password, dsn, wallet_location, wallet_password)
    try:
        for fetched_profile in select_ai.Profile.list(pattern):
            echo_profile(fetched_profile.profile_name)
    finally:
        select_ai.disconnect()


@profile_group.command("translate")
@click.option(
    "--profile",
    "profile_name",
    required=True,
    help="Select AI profile name.",
)
@connection_options
@click.option(
    "--source-language",
    required=True,
    help="Source language for the input text.",
)
@click.option(
    "--target-language",
    required=True,
    help="Target language for the translated text.",
)
@click.argument("text")
def translate(
    profile_name,
    user,
    password,
    dsn,
    wallet_location,
    wallet_password,
    source_language,
    target_language,
    text,
):
    """Translate text using a Select AI profile."""
    connect(user, password, dsn, wallet_location, wallet_password)
    try:
        print_text_result(
            profile(profile_name).translate(
                text=text,
                source_language=source_language,
                target_language=target_language,
            )
        )
    finally:
        select_ai.disconnect()


@profile_group.command("summarize")
@click.option(
    "--profile",
    "profile_name",
    required=True,
    help="Select AI profile name.",
)
@connection_options
@click.option("--prompt", help="Optional prompt to guide the summary.")
@click.option(
    "--location-uri",
    help="URI or local file path containing content to summarize.",
)
@click.option(
    "--file",
    "file_path",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Read local file content and summarize it.",
)
@click.option(
    "--credential-name",
    help="Credential used to access object storage content.",
)
@click.argument("content", required=False)
def summarize(
    profile_name,
    user,
    password,
    dsn,
    wallet_location,
    wallet_password,
    prompt,
    location_uri,
    file_path,
    credential_name,
    content,
):
    """Summarize inline content or content from a location URI."""
    if file_path and content:
        raise click.ClickException(
            "Use either inline content or --file, not both."
        )
    if file_path and location_uri:
        raise click.ClickException(
            "Use either --file or --location-uri, not both."
        )
    if file_path:
        with open(file_path, encoding="utf-8") as file:
            content = file.read()

    connect(user, password, dsn, wallet_location, wallet_password)
    try:
        print_text_result(
            profile(profile_name).summarize(
                content=content,
                prompt=prompt,
                location_uri=location_uri,
                credential_name=credential_name,
            )
        )
    finally:
        select_ai.disconnect()

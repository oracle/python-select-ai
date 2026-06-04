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
    echo_command,
    echo_status,
    print_chunks,
    profile,
)


def _print_help() -> None:
    click.secho("Commands:", fg="cyan")
    echo_command("/help", "Show this help")
    echo_command("/clear", "Start a fresh conversation")
    echo_command("/exit", "Exit the chat session")
    echo_command("/quit", "Exit the chat session")


def _conversation(profile_name: str, conversation_length: int):
    return select_ai.Conversation(
        attributes=select_ai.ConversationAttributes(
            title=f"select-ai chat: {profile_name}",
            conversation_length=conversation_length,
        )
    )


@click.command()
@click.option(
    "--profile",
    "profile_name",
    required=True,
    help="Select AI profile name to use for the chat session.",
)
@connection_options
@click.option(
    "--no-stream",
    is_flag=True,
    help="Print each response after it is fully generated.",
)
@click.option(
    "--chunk-size",
    default=8192,
    show_default=True,
    help="Number of characters to read per streaming chunk.",
)
@click.option(
    "--conversation-length",
    default=10,
    show_default=True,
    help="Number of prompts retained in the conversation context.",
)
@click.option(
    "--keep-conversation",
    is_flag=True,
    help="Keep the database conversation after the REPL exits.",
)
def chat(
    profile_name,
    user,
    password,
    dsn,
    wallet_location,
    wallet_password,
    no_stream,
    chunk_size,
    conversation_length,
    keep_conversation,
):
    """Start a context-aware interactive chat REPL."""
    connect(user, password, dsn, wallet_location, wallet_password)
    prof = profile(profile_name)
    conversation = _conversation(profile_name, conversation_length)

    echo_status(f"Connected to Select AI profile: {profile_name}")
    click.secho(
        "Type /help for commands. Type /exit to quit.", fg="bright_black"
    )

    try:
        while True:
            with prof.chat_session(
                conversation=conversation,
                delete=not keep_conversation,
            ) as session:
                while True:
                    try:
                        prompt = click.prompt(
                            click.style("select_ai", fg="cyan"),
                            prompt_suffix="> ",
                        )
                    except (EOFError, KeyboardInterrupt):
                        click.echo()
                        return

                    prompt = prompt.strip()
                    if not prompt:
                        continue
                    if prompt in ("/exit", "/quit"):
                        return
                    if prompt == "/help":
                        _print_help()
                        continue
                    if prompt == "/clear":
                        conversation = _conversation(
                            profile_name, conversation_length
                        )
                        echo_status("Started a fresh conversation.")
                        break

                    if no_stream:
                        click.echo(session.chat(prompt))
                    else:
                        print_chunks(
                            session.chat(
                                prompt,
                                stream=True,
                                chunk_size=chunk_size,
                            )
                        )
    finally:
        select_ai.disconnect()

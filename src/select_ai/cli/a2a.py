# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import getpass
import json

import click

from select_ai.cli.common import connection_options
from select_ai.version import __version__


@click.group()
def a2a():
    """Serve Select AI database agent teams through A2A."""


@a2a.command()
@click.option("--team", "team_name", required=True, help="Database AI team.")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True, type=int)
@click.option(
    "--public-url",
    help="Public base URL advertised in the A2A Agent Card.",
)
@click.option("--description", help="A2A agent description.")
@click.option(
    "--pool-max-size",
    default=10,
    show_default=True,
    type=click.IntRange(min=1),
    help="Maximum asynchronous Oracle connections.",
)
@connection_options
def serve(
    team_name,
    host,
    port,
    public_url,
    description,
    pool_max_size,
    user,
    password,
    dsn,
    wallet_location,
    wallet_password,
):
    """Start an A2A HTTP server for one database AI agent team."""
    try:
        from select_ai.a2a_server import (
            create_app,
            ensure_a2a_dependencies,
        )

        ensure_a2a_dependencies()
        import uvicorn
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    except ImportError as exc:
        raise click.ClickException(
            "A2A server support requires the optional 'a2a' extra. "
            "Install it with: pip install 'select_ai[a2a]'"
        ) from exc

    if password is None:
        password = getpass.getpass("Database password: ")
    if user is None or dsn is None:
        raise click.ClickException(
            "--user and --dsn (or their SELECT_AI_* environment variables) "
            "are required"
        )
    if public_url is None:
        public_url = f"http://{host}:{port}"

    app = create_app(
        team_name=team_name,
        public_url=public_url,
        user=user,
        password=password,
        dsn=dsn,
        wallet_location=wallet_location,
        wallet_password=wallet_password,
        description=description,
        pool_max_size=pool_max_size,
    )

    click.echo(
        f"A2A Agent Card: {public_url.rstrip('/')}/.well-known/agent-card.json"
    )
    uvicorn.run(app, host=host, port=port)


@a2a.command("agent-card")
@click.option("--team", "team_name", required=True, help="Database AI team.")
@click.option(
    "--public-url",
    required=True,
    help="Public base URL of the A2A server.",
)
@click.option("--description", help="A2A agent description.")
def agent_card(team_name, public_url, description):
    """Print a Gemini Enterprise-compatible A2A v0.3 Agent Card."""
    description = description or (
        f"Oracle Database AI agent team {team_name}."
    )
    endpoint = f"{public_url.rstrip('/')}/a2a/jsonrpc/"
    card = {
        "protocolVersion": "0.3",
        "name": team_name,
        "description": description,
        "url": endpoint,
        "version": __version__,
        "capabilities": {"streaming": True},
        "skills": [
            {
                "id": team_name.lower(),
                "name": team_name,
                "description": description,
                "tags": ["oracle", "database", "select-ai"],
            }
        ],
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
    }
    click.echo(json.dumps(card, indent=2))

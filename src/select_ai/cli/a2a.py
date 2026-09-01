# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import getpass
import json
import ssl

import click

from select_ai.cli.common import connection_options
from select_ai.version import __version__

try:
    import uvicorn

    from select_ai.agent.a2a.server import create_app
except ImportError:
    create_app = None
    uvicorn = None


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
    if create_app is None or uvicorn is None:
        raise click.ClickException(
            "A2A server support requires the optional 'cli' extra. "
            "Install it with: pip install 'select_ai[cli]'"
        )

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


@a2a.command("worker")
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8080, show_default=True, type=int)
@click.option(
    "--session-ttl-seconds",
    default=900,
    show_default=True,
    type=click.IntRange(min=1),
)
@click.option(
    "--session-start-timeout-seconds",
    default=30,
    show_default=True,
    type=click.IntRange(min=1),
)
@click.option(
    "--tls-cert-file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Worker TLS server certificate. Requires all --tls-* options.",
)
@click.option(
    "--tls-key-file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Worker TLS server private key. Requires all --tls-* options.",
)
@click.option(
    "--tls-ca-file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="CA used to validate the gateway client certificate.",
)
def worker(
    host,
    port,
    session_ttl_seconds,
    session_start_timeout_seconds,
    tls_cert_file,
    tls_key_file,
    tls_ca_file,
):
    """Start the internal, in-memory Select AI session worker."""
    try:
        from select_ai.agent.a2a import create_worker_app
    except ImportError as error:
        raise click.ClickException(
            "Worker support requires the optional 'a2a' extra. "
            "Install it with: pip install 'select_ai[a2a]'"
        ) from error

    app = create_worker_app(
        session_ttl_seconds=session_ttl_seconds,
        session_start_timeout_seconds=session_start_timeout_seconds,
    )
    tls_files = (tls_cert_file, tls_key_file, tls_ca_file)
    if any(tls_files) and not all(tls_files):
        raise click.ClickException(
            "Worker mTLS requires --tls-cert-file, --tls-key-file, and "
            "--tls-ca-file."
        )
    uvicorn_options = {}
    if tls_cert_file:
        uvicorn_options = {
            "ssl_certfile": tls_cert_file,
            "ssl_keyfile": tls_key_file,
            "ssl_ca_certs": tls_ca_file,
            "ssl_cert_reqs": ssl.CERT_REQUIRED,
        }
    uvicorn.run(app, host=host, port=port, **uvicorn_options)


@a2a.command("gateway")
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8080, show_default=True, type=int)
@click.option(
    "--agent-url",
    required=True,
    envvar="AGENT_URL",
    help="Public base URL advertised in the gateway Agent Card.",
)
@click.option(
    "--consul-url",
    default="http://consul:8500",
    show_default=True,
    envvar="CONSUL_HTTP_URL",
    help="Consul HTTP API URL.",
)
@click.option(
    "--worker-service",
    default="select-ai-worker",
    show_default=True,
    envvar="WORKER_SERVICE",
    help="Consul service name for Select AI workers.",
)
@click.option(
    "--session-ttl-seconds",
    default=900,
    show_default=True,
    type=click.IntRange(min=1),
    envvar="SESSION_TTL_SECONDS",
)
@click.option(
    "--worker-tls-ca-file",
    envvar="WORKER_TLS_CA_FILE",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="CA bundle used to validate worker certificates.",
)
@click.option(
    "--worker-tls-cert-file",
    envvar="WORKER_TLS_CERT_FILE",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Gateway client certificate used for worker mTLS.",
)
@click.option(
    "--worker-tls-key-file",
    envvar="WORKER_TLS_KEY_FILE",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Gateway client private key used for worker mTLS.",
)
def gateway(
    host,
    port,
    agent_url,
    consul_url,
    worker_service,
    session_ttl_seconds,
    worker_tls_ca_file,
    worker_tls_cert_file,
    worker_tls_key_file,
):
    """Start the public A2A/A2UI database-session gateway."""
    try:
        from select_ai.agent.a2a import GatewaySettings, create_gateway_app
    except ImportError as error:
        raise click.ClickException(
            "Gateway support requires the optional 'a2a' extra. "
            "Install it with: pip install 'select_ai[a2a]'"
        ) from error

    settings = GatewaySettings(
        agent_url=agent_url,
        consul_url=consul_url,
        worker_service=worker_service,
        session_ttl_seconds=session_ttl_seconds,
        worker_tls_ca_file=worker_tls_ca_file,
        worker_tls_cert_file=worker_tls_cert_file,
        worker_tls_key_file=worker_tls_key_file,
    )
    app = create_gateway_app(settings)
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

# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import getpass
import json
import os
import socket
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
@click.option(
    "--deployment",
    type=click.Choice(("standalone", "clustered"), case_sensitive=False),
    default="standalone",
    show_default=True,
    help="A2A runtime deployment topology.",
)
@click.option(
    "--team",
    "team_name",
    envvar="SELECT_AI_A2A_TEAM",
    help="Database AI team. Required for standalone deployment.",
)
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option(
    "--port",
    default=8000,
    show_default=True,
    envvar="PORT",
    type=click.IntRange(min=1, max=65_535),
)
@click.option(
    "--public-url",
    envvar="PUBLIC_URL",
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
@click.option(
    "--consul-url",
    default="http://consul:8500",
    show_default=True,
    envvar="CONSUL_HTTP_URL",
    help="Consul HTTP API URL for clustered deployment.",
)
@click.option(
    "--worker-service",
    default="select-ai-a2a-worker",
    show_default=True,
    envvar="WORKER_SERVICE",
    help="Consul worker service for clustered deployment.",
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
    help="CA bundle used to validate clustered workers.",
)
@click.option(
    "--worker-tls-cert-file",
    envvar="WORKER_TLS_CERT_FILE",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Client certificate presented to clustered workers.",
)
@click.option(
    "--worker-tls-key-file",
    envvar="WORKER_TLS_KEY_FILE",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Client private key presented to clustered workers.",
)
@click.option(
    "--a2ui-form",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Custom A2UI connection-form JSON file.",
)
@connection_options
def serve(
    deployment,
    team_name,
    host,
    port,
    public_url,
    description,
    pool_max_size,
    consul_url,
    worker_service,
    session_ttl_seconds,
    worker_tls_ca_file,
    worker_tls_cert_file,
    worker_tls_key_file,
    a2ui_form,
    user,
    password,
    dsn,
    wallet_location,
    wallet_password,
):
    """Start the public A2A server in standalone or clustered mode."""
    if uvicorn is None:
        raise click.ClickException(
            "A2A server support requires the optional 'cli' extra. "
            "Install it with: pip install 'select_ai[cli]'"
        )

    if public_url is None:
        public_url = f"http://{host}:{port}"

    if deployment == "standalone":
        if create_app is None:
            raise click.ClickException(
                "Standalone A2A support requires the optional 'cli' extra. "
                "Install it with: pip install 'select_ai[cli]'"
            )
        if team_name is None:
            raise click.ClickException(
                "--team or SELECT_AI_A2A_TEAM is required for standalone "
                "deployment"
            )
        if user is None or dsn is None:
            raise click.ClickException(
                "--user and --dsn (or their SELECT_AI_* environment "
                "variables) are required for standalone deployment"
            )
        if password is None:
            password = getpass.getpass("Database password: ")
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
    else:
        try:
            from select_ai.agent.a2a import (
                ConnectionConfig,
                GatewaySettings,
                create_gateway_app,
            )
            from select_ai.agent.a2a.forms import load_connection_form
        except ImportError as error:
            raise click.ClickException(
                "Clustered A2A support requires the optional 'a2a' extra. "
                "Install it with: pip install 'select_ai[a2a]'"
            ) from error

        connection = ConnectionConfig(
            dsn=dsn,
            username=user,
            password=password,
            team_name=team_name,
        )
        form_template = None
        if a2ui_form:
            try:
                form_template = load_connection_form(
                    a2ui_form,
                    connection.missing_fields,
                )
            except ValueError as error:
                raise click.ClickException(str(error)) from error
        settings = GatewaySettings(
            public_url=public_url,
            consul_url=consul_url,
            worker_service=worker_service,
            session_ttl_seconds=session_ttl_seconds,
            worker_tls_ca_file=worker_tls_ca_file,
            worker_tls_cert_file=worker_tls_cert_file,
            worker_tls_key_file=worker_tls_key_file,
            connection=connection,
            connection_form_template=form_template,
        )
        app = create_gateway_app(settings)

    click.echo(
        f"A2A Agent Card: {public_url.rstrip('/')}/.well-known/agent-card.json"
    )
    uvicorn.run(app, host=host, port=port)


@a2a.command("worker")
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option(
    "--port",
    default=8080,
    show_default=True,
    type=click.IntRange(min=1, max=65_535),
)
@click.option(
    "--worker-id",
    envvar="WORKER_ID",
    default=socket.gethostname,
    show_default="host name",
    help="Unique worker ID registered with Consul.",
)
@click.option(
    "--consul-url",
    envvar="CONSUL_HTTP_URL",
    default="http://consul:8500",
    show_default=True,
    help="Consul HTTP API URL.",
)
@click.option(
    "--worker-endpoint",
    envvar="WORKER_ENDPOINT",
    help="Worker URL advertised through Consul, including scheme and port.",
)
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
    worker_id,
    consul_url,
    worker_endpoint,
    session_ttl_seconds,
    session_start_timeout_seconds,
    tls_cert_file,
    tls_key_file,
    tls_ca_file,
):
    """Start the internal Select AI session worker."""
    try:
        from select_ai.agent.a2a import WorkerSettings, create_worker_app
    except ImportError as error:
        raise click.ClickException(
            "Worker support requires the optional 'a2a' extra. "
            "Install it with: pip install 'select_ai[a2a]'"
        ) from error

    settings = WorkerSettings(
        consul_url=consul_url,
        worker_id=worker_id,
        worker_address=os.environ.get("WORKER_ADDRESS", socket.gethostname()),
        worker_port=port,
        session_ttl_seconds=session_ttl_seconds,
        session_start_timeout_seconds=session_start_timeout_seconds,
        worker_endpoint=worker_endpoint,
    )
    app = create_worker_app(settings)
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

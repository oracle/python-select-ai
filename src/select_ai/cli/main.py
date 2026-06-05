# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

try:
    import click
except ImportError:

    def cli():
        raise SystemExit(
            "The Select AI CLI requires the optional 'cli' extra. "
            "Install it with: pip install 'select_ai[cli]'"
        )

else:
    from select_ai.cli.chat import chat
    from select_ai.cli.profile import profile_group
    from select_ai.cli.sql import sql

    @click.group(context_settings={"help_option_names": ["-h", "--help"]})
    def cli():
        """Command line tools for Select AI."""

    cli.add_command(chat)
    cli.add_command(sql)
    cli.add_command(profile_group, "profile")


if __name__ == "__main__":
    cli()

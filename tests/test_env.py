# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import os
import sys
import secrets
import string
import select_ai

# dictionary containing all parameters; these are acquired as needed by the
# methods below (which should be used instead of consulting this dictionary
# directly) and then stored so that a value is not requested more than once
PARAMETERS = {}


# -------------------------
# PARAMETER ACCESS HELPERS
# -------------------------
def get_value(name, default_value=None, **kwargs):
    """Retrieve a value from PARAMETERS or environment."""
    if name in PARAMETERS:
        return PARAMETERS[name]

    env_name = "SAI_TEST_" + name
    value = os.environ.get(env_name)

    if not value:
        value = default_value

    PARAMETERS[name] = value
    return value


def get_connection_args():
    """Get and return connection parameters"""
    return {
        "user": get_test_user(),
        "password": get_test_password(),
        "dsn": get_connect_string(),
        "wallet_location": get_wallet_location(),
        "wallet_password": get_wallet_password(),
    }


def create_connection(use_wallet=True, **kwargs):
    """Create a synchronous connection."""
    conn_args = get_connection_args()

    connect_kwargs = {
        "user": kwargs.get("user", conn_args["user"]),
        "password": kwargs.get("password", conn_args["password"]),
        "dsn": kwargs.get("dsn", conn_args["dsn"]),
    }

    if use_wallet:
        connect_kwargs.update({
            "config_dir": kwargs.get("wallet_location", conn_args["wallet_location"]),
            "wallet_location": kwargs.get("wallet_location", conn_args["wallet_location"]),
            "wallet_password": kwargs.get("wallet_password", conn_args["wallet_password"])
        })

    select_ai.connect(**connect_kwargs)


async def create_async_connection(use_wallet=True, **kwargs):
    """Create an asynchronous connection."""
    conn_args = get_connection_args()

    connect_kwargs = {
        "user": kwargs.get("user", conn_args["user"]),
        "password": kwargs.get("password", conn_args["password"]),
        "dsn": kwargs.get("dsn", conn_args["dsn"]),
    }

    if use_wallet:
        connect_kwargs.update({
            "config_dir": kwargs.get("wallet_location", conn_args["wallet_location"]),
            "wallet_location": kwargs.get("wallet_location", conn_args["wallet_location"]),
            "wallet_password": kwargs.get("wallet_password", conn_args["wallet_password"])
        })

    print(connect_kwargs)
    await select_ai.async_connect(**connect_kwargs)



# ---------------------
# SIMPLE VALUE HELPERS
# ---------------------
def get_connect_string():
    """Retrieve the database connection string used for testing."""
    return get_value("CONNECT_STRING", default_value="Connect String")


def get_test_password():
    """Retrieve the test password, possibly from environment or set a default."""
    return get_value("PASSWORD", default_value=f"Password for {get_test_user()}", password=True)


def get_test_user():
    """Retrieve the test user name, or use a default value."""
    return get_value("USER", default_value="Test User Name")


def get_use_wallet():
    """Check if a PDB wallet should be used for the connection."""
    return get_value("USE_WALLET", default_value=False)


def get_wallet_location():
    """Retrieve the file path for the wallet location, if specified."""
    return get_value("WALLET_LOCATION", default_value=None)


def get_wallet_password():
    """Retrieve the password for accessing the wallet."""
    return get_value("WALLET_PASSWORD", default_value="Wallet Password", password=True)


def get_cred_username():
    """Retrieve the OCI credential username (for cloud authentication)."""
    return get_value("CRED_USERNAME", default_value="OCI credential username")


def get_cred_password():
    """Retrieve the OCI credential password (for cloud authentication)."""
    return get_value("CRED_PASSWORD", default_value="OCI credential password")


def get_user_ocid():
    """Retrieve the OCID for the user in OCI."""
    return get_value("USER_OCID", default_value="user ocid")


def get_tenancy_ocid():
    """Retrieve the OCID for the tenancy in OCI."""
    return get_value("TENANCY_OCID", default_value="tenancy ocid")


def get_private_key():
    """Retrieve the private key used for authentication or signing."""
    return get_value("PRIVATE_KEY", default_value="private key")


def get_fingerprint():
    """Retrieve the fingerprint for the private key used in OCI."""
    return get_value("FINGERPRINT", default_value="fingerprint")


def get_compartment_id(provider="OCI"):
    """Retrieve the compartment OCID for a given cloud provider (default: OCI)."""
    return get_value(f"{provider}_COMP_ID", default_value="Compartment ID")


def get_embedding_location():
    """Retrieve the file or folder location for storing vector embeddings."""
    return get_value("EMBEDDING_LOCATION", default_value="Vector Embedding Location")


def get_random_string(length=10):
    """Generate a random string of the specified length, using ASCII letters."""
    return "".join(secrets.choice(string.ascii_letters) for i in range(length))


# ------------------
# SQL SCRIPT HELPER
# ------------------
def run_sql_script(conn, script_name, **kwargs):
    statement_parts = []
    cursor = conn.cursor()
    replace_values = [("&" + k + ".", v) for k, v in kwargs.items()] + [
        ("&" + k, v) for k, v in kwargs.items()
    ]
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    file_name = os.path.join(script_dir, "sql", script_name + ".sql")
    for line in open(file_name):
        if line.strip() == "/":
            statement = "".join(statement_parts).strip()
            if statement:
                for search_value, replace_value in replace_values:
                    statement = statement.replace(search_value, replace_value)
                try:
                    cursor.execute(statement)
                except:
                    print("Failed to execute SQL:", statement)
                    raise
            statement_parts = []
        else:
            statement_parts.append(line)
    cursor.execute(
        """
        select name, type, line, position, text
        from dba_errors
        where owner = upper(:owner)
        order by name, type, line, position
        """,
        owner=get_test_user(),
    )
    prev_name = prev_obj_type = None
    for name, obj_type, line_num, position, text in cursor:
        if name != prev_name or obj_type != prev_obj_type:
            print("%s (%s)" % (name, obj_type))
            prev_name = name
            prev_obj_type = obj_type
        print("    %s/%s %s" % (line_num, position, text))


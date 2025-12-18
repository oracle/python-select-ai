# -----------------------------------------------------------------------------
# Copyright (c) 2020, 2025, Oracle and/or its affiliates.
#
# This software is dual-licensed to you under the Universal Permissive License
# (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl and Apache License
# 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose
# either license.
#
# If you elect to accept the software under the Apache License, Version 2.0,
# the following applies:
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# -----------------------------------------------------------------------------

import importlib
import os
import secrets
import sys
import string
import unittest
from threading import get_ident
from typing import Dict, Hashable

import select_ai
import oracledb

# __conn__: Dict[Hashable, oracledb.Connection] = {}
# __async_conn__: Dict[Hashable, oracledb.AsyncConnection] = {}

DEFAULT_MAIN_USER = "admin"
DEFAULT_CONNECT_STRING = "localhost:1531/GCC59E2CF7A6F5F_ADWP"
DEFAULT_PROXY_USER = "selectai_testuser"


# dictionary containing all parameters; these are acquired as needed by the
# methods below (which should be used instead of consulting this dictionary
# directly) and then stored so that a value is not requested more than once
PARAMETERS = {}


def _initialize():
    """
    Performs initialization of the select_ai environment.
    Ensures that OracleDB mode is set and required plugins are imported.
    """
    if PARAMETERS.get("INITIALIZED"):
        return

    # Initialize Oracle client if needed
    if not get_is_thin() and oracledb.is_thin_mode():
        oracledb.init_oracle_client()
        oracledb.defaults.thick_mode_dsn_passthrough = False

    # Load select_ai plugins from environment variable
    plugin_names = os.environ.get("SAI_TEST_PLUGINS")
    if plugin_names:
        for name in plugin_names.split(","):
            module_name = f"oracledb.plugins.{name.strip()}"
            print(f"Importing module: {module_name}")
            importlib.import_module(module_name)

    PARAMETERS["INITIALIZED"] = True


def run_test_cases():
    unittest.main(testRunner=unittest.TextTestRunner(verbosity=2))


def get_value(name, label, default_value=None, password=False):
    """Retrieve a value from PARAMETERS or environment."""
    if name in PARAMETERS:
        return PARAMETERS[name]

    env_name = "SAI_TEST_" + name
    value = os.environ.get(env_name)

    if not value:
        value = default_value

    PARAMETERS[name] = value
    return value


def get_client_version():
    name = "CLIENT_VERSION"
    value = PARAMETERS.get(name)
    if value is None:
        _initialize()
        value = oracledb.clientversion()[:2]
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


def get_connect_string():
    return get_value(
        "CONNECT_STRING", "Connect String", DEFAULT_CONNECT_STRING
    )

def get_localhost_connect_string():
    return "localhost:1531/GCC59E2CF7A6F5F_ADWP"


def get_is_thin():
    driver_mode = get_value("DRIVER_MODE", "Driver mode (thin|thick)", "thin")
    return driver_mode == "thin"


def get_test_password():
    return get_value(
        "PASSWORD", f"Password for {get_test_user()}", password=True
    )


def get_test_user():
    return get_value("USER", "Test User Name", DEFAULT_MAIN_USER)

def get_proxy_user():
    return get_value("PROXY_USER", "Proxy User Name", DEFAULT_PROXY_USER)


def get_wallet_location():
    return get_value("WALLET_LOCATION", "Wallet Location")


def get_cred_username():
    return get_value("CRED_USERNAME", "OCI credential username")


def get_cred_password():
    return get_value("CRED_PASSWORD", "OCI credential password")


def get_user_ocid():
    return get_value("USER_OCID", "user ocid")


def get_tenancy_ocid():
    return get_value("TENANCY_OCID", "tenancy ocid")


def get_private_key():
    return get_value("PRIVATE_KEY", "private key")


def get_fingerprint():
    return get_value("FINGERPRINT", "fingerprint")


def get_wallet_password():
    return get_value("WALLET_PASSWORD", "Wallet Password", password=True)


def get_compartment_id(provider="OCI"):
    return get_value(f"{provider}_COMPARTMENT_ID", "Compartment ID")


def get_embedding_location():
    return get_value("EMBEDDING_LOCATION", "Vector Embedding Location")


def get_random_string(length=10):
    return "".join(secrets.choice(string.ascii_letters) for i in range(length))


def has_client_version(major_version, minor_version=0):
    if get_is_thin():
        return True
    return get_client_version() >= (major_version, minor_version)


def has_server_version(major_version, minor_version=0):
    return get_server_version() >= (major_version, minor_version)


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


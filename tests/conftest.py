# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

#  Set values in environment variables
#
#   PYSAI_TEST_USER: user to run select ai operations
#   PYSAI_TEST_USER_PASSWORD: user's password to run select ai operations
#   PYSAI_TEST_ADMIN_USER: administrative user for test suite
#   PYSAI_TEST_ADMIN_PASSWORD: administrative password for test suite
#   PYSAI_TEST_CONNECT_STRING: connect string for test suite
#   PYSAI_TEST_WALLET_LOCATION: location of wallet file (thin mode, mTLS)
#   PYSAI_TEST_WALLET_PASSWORD: password for wallet file (thin mode, mTLS)
#
#           OCI Gen AI
#   PYSAI_TEST_OCI_USER_OCID
#   PYSAI_TEST_OCI_TENANCY_OCID
#   PYSAI_TEST_OCI_PRIVATE_KEY
#   PYSAI_TEST_OCI_FINGERPRINT
#   PYSAI_TEST_OCI_COMPARTMENT_ID
#
#           OpenAI
#   PYSAI_TEST_OPENAI_API_KEY

import os
import uuid

import pytest
import select_ai

PYSAI_TEST_USER = "PYSAI_TEST_USER"
PYSAI_OCI_CREDENTIAL_NAME = f"PYSAI_OCI_CREDENTIAL_{uuid.uuid4().hex.upper()}"


def get_env_value(name, default_value=None, required=False):
    """
    Returns the value of the environment variable if it is present and the
    default value if it is not. If marked as required, the test suite will
    immediately fail.
    """
    env_name = f"PYSAI_TEST_{name}"
    value = os.environ.get(env_name)
    if value is None:
        if required:
            msg = f"missing value for environment variable {env_name}"
            pytest.exit(msg, 1)
        return default_value
    return value


class TestEnv:

    def __init__(self):
        self.test_user = get_env_value("USER", default_value="PYSAI_TEST_USER")
        self.test_user_password = get_env_value("USER_PASSWORD", required=True)
        self.connect_string = get_env_value("CONNECT_STRING", required=True)
        self.admin_user = get_env_value("ADMIN_USER", default_value="admin")
        self.admin_password = get_env_value("ADMIN_PASSWORD")
        self.wallet_location = get_env_value("WALLET_LOCATION")
        self.wallet_password = get_env_value("WALLET_PASSWORD")

    def connect_params(self, admin: bool = False):
        """
        Returns connect params
        """
        user = self.admin_user if admin else self.test_user
        password = self.admin_password if admin else self.test_user_password
        connect_params = {
            "user": user,
            "password": password,
            "dsn": self.connect_string,
            "wallet_location": self.wallet_location,
            "wallet_password": self.wallet_password,
            "config_dir": self.wallet_location,
        }
        return connect_params


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def test_env(pytestconfig):
    env = TestEnv()
    return env


@pytest.fixture(autouse=True, scope="session")
def setup_test_user(test_env):
    select_ai.connect(**test_env.connect_params(admin=True))
    select_ai.grant_privileges(users=[test_env.test_user])
    select_ai.grant_http_access(
        users=[test_env.test_user],
        provider_endpoint=select_ai.OpenAIProvider.provider_endpoint,
    )
    select_ai.disconnect()


@pytest.fixture(autouse=True, scope="session")
def connect(setup_test_user, test_env):
    select_ai.connect(**test_env.connect_params())
    yield
    select_ai.disconnect()


@pytest.fixture(autouse=True, scope="session")
async def async_connect(setup_test_user, test_env, anyio_backend):
    await select_ai.async_connect(**test_env.connect_params())
    yield
    await select_ai.async_disconnect()


@pytest.fixture
def connection():
    return select_ai.db.get_connection()


@pytest.fixture
def async_connection():
    return select_ai.db.async_get_connection()


@pytest.fixture
def cursor():
    with select_ai.cursor() as cr:
        yield cr


@pytest.fixture
async def async_cursor():
    async with select_ai.async_cursor() as cr:
        yield cr


@pytest.fixture(autouse=True, scope="session")
def oci_credential(connect, test_env):
    credential = {
        "credential_name": PYSAI_OCI_CREDENTIAL_NAME,
        "user_ocid": get_env_value("OCI_USER_OCID", required=True),
        "tenancy_ocid": get_env_value("OCI_TENANCY_OCID", required=True),
        "private_key": get_env_value("OCI_PRIVATE_KEY", required=True),
        "fingerprint": get_env_value("OCI_FINGERPRINT", required=True),
    }
    select_ai.create_credential(credential, replace=True)
    yield credential
    select_ai.delete_credential(PYSAI_OCI_CREDENTIAL_NAME)


@pytest.fixture(scope="module")
def oci_compartment_id(test_env):
    return get_env_value("OCI_COMPARTMENT_ID", required=True)

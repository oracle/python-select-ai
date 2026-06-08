# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import os

import pytest


def get_credential_env_value(name, default_value=None):
    return os.environ.get(f"PYSAI_TEST_{name}", default_value)


@pytest.fixture(scope="session")
def oci_credential():
    """
    Override the root autouse OCI credential fixture for credential-only tests.
    These suites should not require OCI environment variables unless a test
    explicitly opts into them.
    """
    return None


@pytest.fixture(scope="session")
def credential_test_params(test_env):
    return {
        "user": test_env.test_user,
        "password": test_env.test_user_password,
        "dsn": test_env.connect_string,
        "user_ocid": get_credential_env_value(
            "OCI_USER_OCID", default_value="user ocid"
        ),
        "tenancy_ocid": get_credential_env_value(
            "OCI_TENANCY_OCID", default_value="tenancy ocid"
        ),
        "private_key": get_credential_env_value(
            "OCI_PRIVATE_KEY", default_value="private key"
        ),
        "fingerprint": get_credential_env_value(
            "OCI_FINGERPRINT", default_value="fingerprint"
        ),
        "cred_username": get_credential_env_value(
            "CRED_USERNAME", default_value="OCI credential username"
        ),
        "cred_password": get_credential_env_value(
            "CRED_PASSWORD", default_value="OCI credential password"
        ),
    }

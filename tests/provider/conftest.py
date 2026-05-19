# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import importlib.util
from pathlib import Path

import pytest
import select_ai

_BASIC_SCHEMA_PRIVILEGES = (
    "CREATE SESSION",
    "CREATE TABLE",
    "UNLIMITED TABLESPACE",
)
_ROOT_CONFTEST_PATH = Path(__file__).resolve().parents[1] / "conftest.py"


def _load_root_test_env_class():
    spec = importlib.util.spec_from_file_location(
        "tests_root_conftest",
        _ROOT_CONFTEST_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.TestEnv


def get_supported_provider_endpoints():
    """
    Returns provider endpoints that can be derived directly from the public
    provider classes and are therefore suitable for ACL enable/disable tests.
    OCI is intentionally not included here because its endpoint is deployment
    specific and not exposed as one canonical default by OCIGenAIProvider.
    """
    return {
        "openai": select_ai.OpenAIProvider.provider_endpoint,
        "cohere": select_ai.CohereProvider.provider_endpoint,
        "google": select_ai.GoogleProvider.provider_endpoint,
        "huggingface": select_ai.HuggingFaceProvider.provider_endpoint,
        "anthropic": select_ai.AnthropicProvider.provider_endpoint,
        "azure": select_ai.AzureProvider(
            azure_resource_name="python-select-ai-test"
        ).provider_endpoint,
        "aws": select_ai.AWSProvider(region="us-east-1").provider_endpoint,
    }


@pytest.fixture(scope="session")
def oci_credential():
    """
    Provider tests do not need the shared OCI credential fixture.
    """
    return None


@pytest.fixture(scope="session")
def test_env(pytestconfig):
    env = _load_root_test_env_class()()
    env.test_user = env.admin_user
    env.test_user_password = env.admin_password
    return env


def ensure_provider_test_user_exists(username: str, password: str):
    username_upper = username.upper()
    with select_ai.cursor() as cr:
        cr.execute(
            "SELECT 1 FROM dba_users WHERE username = :username",
            username=username_upper,
        )
        if cr.fetchone():
            return
        escaped_password = password.replace('"', '""')
        cr.execute(
            f'CREATE USER {username_upper} IDENTIFIED BY "{escaped_password}"'
        )
    with select_ai.db.get_connection() as conn:
        conn.commit()


def grant_provider_test_user_privileges(username: str):
    username_upper = username.upper()
    with select_ai.cursor() as cr:
        for privilege in _BASIC_SCHEMA_PRIVILEGES:
            cr.execute(f"GRANT {privilege} TO {username_upper}")
    with select_ai.db.get_connection() as conn:
        conn.commit()


async def async_ensure_provider_test_user_exists(username: str, password: str):
    username_upper = username.upper()
    async with select_ai.async_cursor() as cr:
        await cr.execute(
            "SELECT 1 FROM dba_users WHERE username = :username",
            username=username_upper,
        )
        if await cr.fetchone():
            return
        escaped_password = password.replace('"', '""')
        await cr.execute(
            f'CREATE USER {username_upper} IDENTIFIED BY "{escaped_password}"'
        )
    async with select_ai.db.async_get_connection() as async_connection:
        await async_connection.commit()


async def async_grant_provider_test_user_privileges(username: str):
    username_upper = username.upper()
    async with select_ai.async_cursor() as cr:
        for privilege in _BASIC_SCHEMA_PRIVILEGES:
            await cr.execute(f"GRANT {privilege} TO {username_upper}")
    async with select_ai.db.async_get_connection() as async_connection:
        await async_connection.commit()

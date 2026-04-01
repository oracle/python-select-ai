# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import contextlib
import json
import os
import uuid

import pytest
import select_ai

_BASIC_SCHEMA_PRIVILEGES = (
    "CREATE SESSION",
    "CREATE TABLE",
    "UNLIMITED TABLESPACE",
)

_PROVIDER_CLASSES = {
    "openai": select_ai.OpenAIProvider,
    "azure": select_ai.AzureProvider,
    "oci": select_ai.OCIGenAIProvider,
    "cohere": select_ai.CohereProvider,
    "google": select_ai.GoogleProvider,
    "anthropic": select_ai.AnthropicProvider,
    "huggingface": select_ai.HuggingFaceProvider,
    "aws": select_ai.AWSProvider,
}


@pytest.fixture(autouse=True, scope="module")
def connect():
    yield


@pytest.fixture(autouse=True, scope="module")
def async_connect():
    yield


@pytest.fixture(autouse=True, scope="module")
def oci_credential():
    yield {}


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


def _env(name, default=None):
    return os.environ.get(name, default)


def _required_env(name, fallback=None):
    value = _env(name, fallback)
    if not value:
        pytest.skip(f"missing environment variable {name}")
    return value


def _ensure_test_user_exists(username: str, password: str):
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


def _grant_basic_schema_privileges(username: str):
    username_upper = username.upper()
    with select_ai.cursor() as cr:
        for privilege in _BASIC_SCHEMA_PRIVILEGES:
            cr.execute(f"GRANT {privilege} TO {username_upper}")
    with select_ai.db.get_connection() as conn:
        conn.commit()


class ProviderTestEnv:

    def __init__(self):
        self.test_user = _required_env(
            "PYSAI_PROVIDER_TEST_USER", _env("PYSAI_TEST_USER")
        )
        self.test_user_password = _required_env(
            "PYSAI_PROVIDER_TEST_USER_PASSWORD",
            _env("PYSAI_TEST_USER_PASSWORD"),
        )
        self.admin_user = _required_env(
            "PYSAI_PROVIDER_TEST_ADMIN_USER", _env("PYSAI_TEST_ADMIN_USER")
        )
        self.admin_password = _required_env(
            "PYSAI_PROVIDER_TEST_ADMIN_PASSWORD",
            _env("PYSAI_TEST_ADMIN_PASSWORD"),
        )
        self.connect_string = _required_env(
            "PYSAI_PROVIDER_TEST_CONNECT_STRING",
            _env("PYSAI_TEST_CONNECT_STRING"),
        )
        self.wallet_location = _env(
            "PYSAI_PROVIDER_TEST_WALLET_LOCATION",
            _env("PYSAI_TEST_WALLET_LOCATION"),
        )
        self.wallet_password = _env(
            "PYSAI_PROVIDER_TEST_WALLET_PASSWORD",
            _env("PYSAI_TEST_WALLET_PASSWORD"),
        )

    def connect_params(self, admin=False):
        user = self.admin_user if admin else self.test_user
        password = self.admin_password if admin else self.test_user_password
        params = {
            "user": user,
            "password": password,
            "dsn": self.connect_string,
        }
        if self.wallet_location:
            params["wallet_location"] = self.wallet_location
            params["wallet_password"] = self.wallet_password
            params["config_dir"] = self.wallet_location
        return params


def _provider_json_env(provider_name, suffix):
    env_name = f"PYSAI_PROVIDER_{provider_name.upper()}_{suffix}"
    raw = os.environ.get(env_name)
    if not raw:
        pytest.skip(f"missing environment variable {env_name}")
    return json.loads(raw)


def _provider_prompt(provider_name):
    return os.environ.get(
        f"PYSAI_PROVIDER_{provider_name.upper()}_PROMPT",
        "What is a database?",
    )


def _build_provider(provider_name, provider_kwargs):
    provider_cls = _PROVIDER_CLASSES[provider_name]
    return provider_cls(**provider_kwargs)


@pytest.fixture(scope="session")
def provider_test_env():
    return ProviderTestEnv()


@pytest.fixture(autouse=True, scope="session")
def setup_test_user(provider_test_env):
    select_ai.connect(**provider_test_env.connect_params(admin=True))
    _ensure_test_user_exists(
        username=provider_test_env.test_user,
        password=provider_test_env.test_user_password,
    )
    _grant_basic_schema_privileges(username=provider_test_env.test_user)
    select_ai.grant_privileges(users=[provider_test_env.test_user])
    select_ai.disconnect()
    yield


@pytest.fixture(autouse=True, scope="module")
def provider_connection(setup_test_user, provider_test_env):
    select_ai.connect(**provider_test_env.connect_params())
    yield
    with contextlib.suppress(Exception):
        select_ai.disconnect()


@pytest.fixture
def provider_profile_factory(provider_test_env):
    created = []

    def _factory(provider_name):
        credential = _provider_json_env(provider_name, "CREDENTIAL_JSON")
        provider_kwargs = _provider_json_env(provider_name, "PROFILE_JSON")
        provider = _build_provider(provider_name, provider_kwargs)
        credential_name = (
            f"PYSAI_{provider_name.upper()}_CRED_{uuid.uuid4().hex.upper()}"
        )
        profile_name = (
            f"PYSAI_{provider_name.upper()}_PROFILE_{uuid.uuid4().hex.upper()}"
        )
        credential["credential_name"] = credential_name
        select_ai.create_credential(credential=credential, replace=True)
        provider_endpoint = (
            provider.provider_endpoint
            or getattr(provider.__class__, "provider_endpoint", None)
        )
        if provider_endpoint:
            select_ai.grant_http_access(
                users=[provider_test_env.test_user],
                provider_endpoint=provider_endpoint,
            )
        profile = select_ai.Profile(
            profile_name=profile_name,
            attributes=select_ai.ProfileAttributes(
                credential_name=credential_name,
                provider=provider,
            ),
        )
        created.append((provider_endpoint, credential_name, profile))
        return profile, _provider_prompt(provider_name)

    yield _factory

    for provider_endpoint, credential_name, profile in reversed(created):
        with contextlib.suppress(Exception):
            profile.delete(force=True)
        with contextlib.suppress(Exception):
            select_ai.delete_credential(credential_name, force=True)
        if provider_endpoint:
            with contextlib.suppress(Exception):
                select_ai.revoke_http_access(
                    users=[provider_test_env.test_user],
                    provider_endpoint=provider_endpoint,
                )

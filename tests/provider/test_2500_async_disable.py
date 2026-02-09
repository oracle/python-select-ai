# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import logging

import oracledb
import pytest
import select_ai
from provider.conftest import (
    async_ensure_provider_test_user_exists,
    async_grant_provider_test_user_privileges,
    get_supported_provider_endpoints,
)

logger = logging.getLogger("TestAsyncDisableProvider")

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="class", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )


@pytest.fixture(scope="class")
def disable_params(request, test_env):
    request.cls.disable_params = {
        "user": test_env.admin_user,
        "password": test_env.admin_password,
        "dsn": test_env.connect_string,
    }


@pytest.fixture(scope="class", autouse=True)
async def setup_and_teardown(request, async_connect, disable_params, test_env):
    logger.info("=== Setting up TestAsyncDisableProvider class ===")
    await select_ai.async_disconnect()
    await select_ai.async_connect(**test_env.connect_params(admin=True))
    assert await select_ai.async_is_connected(), "Connection to DB failed"

    db_users = []
    try:
        for i in range(1, 6):
            user = f"DB_USER{i}"
            await request.cls.create_local_user(user)
            db_users.append(user)
        request.cls.db_users = db_users
        await request.cls.create_local_user("DB_USER6")
    except Exception:
        await select_ai.async_disconnect()
        await select_ai.async_connect(**test_env.connect_params())
        raise

    yield

    logger.info("=== Tearing down TestAsyncDisableProvider class ===")
    db_users.append("DB_USER6")
    async with select_ai.async_cursor() as admin_cursor:
        for user in db_users:
            try:
                await admin_cursor.execute(f"DROP USER {user} CASCADE")
            except oracledb.DatabaseError as exc:
                logger.warning("Drop user failed for %s: %s", user, exc)
    try:
        await select_ai.async_disconnect()
    except Exception as exc:
        logger.warning("Warning: disconnect failed (%s)", exc)
    await select_ai.async_connect(**test_env.connect_params())


@pytest.fixture(autouse=True)
async def provider_enabled_state(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    provider_endpoint = "*.openai.azure.com"
    await select_ai.async_grant_http_access(
        users=request.cls.db_users,
        provider_endpoint=provider_endpoint,
    )
    yield
    logger.info("--- Finished test: %s ---", request.function.__name__)


@pytest.mark.usefixtures("disable_params", "setup_and_teardown")
class TestAsyncDisableProvider:
    @classmethod
    async def create_local_user(cls, test_username="TEST_USER1"):
        test_password = cls.disable_params["password"]
        async with select_ai.async_cursor() as admin_cursor:
            try:
                await admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            except oracledb.DatabaseError:
                pass
        await async_ensure_provider_test_user_exists(test_username, test_password)
        await async_grant_provider_test_user_privileges(test_username)
        await select_ai.async_grant_privileges(users=[test_username])

    def setup_method(self):
        self.provider_endpoint = "*.openai.azure.com"

    async def test_2501(self):
        """Test disabling provider with all valid users and endpoint."""
        try:
            await select_ai.async_revoke_http_access(
                users=self.db_users,
                provider_endpoint=self.provider_endpoint,
            )
            logger.info("Provider disabled successfully for all valid users.")
        except Exception as exc:
            pytest.fail(
                f"async_revoke_http_access() raised {exc} unexpectedly."
            )

    async def test_2502(self):
        """Test disabling provider with a mix of existing and non-existent usernames."""
        db_users = ["DB_USER1", "TEST_USER2"]
        with pytest.raises(oracledb.DatabaseError):
            await select_ai.async_revoke_http_access(
                users=db_users,
                provider_endpoint=self.provider_endpoint,
            )

    async def test_2503(self):
        """Test disabling provider with all invalid usernames."""
        with pytest.raises(oracledb.DatabaseError):
            await select_ai.async_revoke_http_access(
                users=["INVALID_USER1", "INVALID_USER2"],
                provider_endpoint=self.provider_endpoint,
            )

    async def test_2504(self):
        """Test disabling provider with users as integer."""
        with pytest.raises((TypeError, ValueError)):
            await select_ai.async_revoke_http_access(
                users=123,
                provider_endpoint=self.provider_endpoint,
            )

    async def test_2505(self):
        """Test disabling provider with users as string."""
        try:
            await select_ai.async_revoke_http_access(
                users="DB_USER1",
                provider_endpoint=self.provider_endpoint,
            )
            logger.info("Provider disabled successfully for string user input.")
        except Exception as exc:
            pytest.fail(
                f"async_revoke_http_access() raised {exc} unexpectedly."
            )

    async def test_2506(self):
        """Test disabling provider with users as None."""
        with pytest.raises((TypeError, ValueError)):
            await select_ai.async_revoke_http_access(
                users=None,
                provider_endpoint=self.provider_endpoint,
            )

    async def test_2507(self):
        """Test disabling provider with missing provider_endpoint."""
        with pytest.raises(oracledb.DatabaseError, match=r"ORA-29261: bad argument"):
            await select_ai.async_revoke_http_access(
                users=self.db_users,
                provider_endpoint=None,
            )

    async def test_2508(self):
        """Test disabling provider with invalid endpoint."""
        with pytest.raises(oracledb.DatabaseError):
            await select_ai.async_revoke_http_access(
                users=self.db_users,
                provider_endpoint="invalid.endpoint",
            )

    async def test_2509(self):
        """Test disabling provider with empty users list."""
        try:
            await select_ai.async_revoke_http_access(
                users=[],
                provider_endpoint=self.provider_endpoint,
            )
            logger.info("async_revoke_http_access() succeeded with empty users.")
        except Exception as exc:
            pytest.fail(
                "async_revoke_http_access() raised "
                f"{exc} unexpectedly with empty users."
            )

    async def test_2510(self):
        """Test disabling provider with duplicate usernames."""
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_revoke_http_access(
                users=[self.db_users[0], self.db_users[0]],
                provider_endpoint=self.provider_endpoint,
            )
        assert "ORA-01927" in str(exc_info.value)

    async def test_2511(self):
        """Test disabling provider with lowercase username."""
        try:
            await select_ai.async_revoke_http_access(
                users=[self.db_users[0].lower()],
                provider_endpoint=self.provider_endpoint,
            )
            logger.info("Provider disabled successfully for lowercase username.")
        except Exception as exc:
            pytest.fail(
                "async_revoke_http_access() raised "
                f"{exc} unexpectedly with lowercase username."
            )

    async def test_2512(self):
        """Test disabling provider with username containing whitespace."""
        db_users = [f"  {self.db_users[0]}  "]
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_revoke_http_access(
                users=db_users,
                provider_endpoint=self.provider_endpoint,
            )
        assert "ORA-01927" in str(exc_info.value)

    async def test_2513(self):
        """Test disabling provider with valid custom endpoint."""
        with pytest.raises(
            oracledb.DatabaseError,
            match=r"ORA-24244: invalid host or port for access control list \(ACL\) assignment",
        ):
            await select_ai.async_revoke_http_access(
                users=self.db_users,
                provider_endpoint="https://custom.openai.azure.com",
            )

    async def test_2514(self):
        """Test disabling provider with non-granted user."""
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_revoke_http_access(
                users=["DB_USER6"],
                provider_endpoint=self.provider_endpoint,
            )
        assert "ORA-01927" in str(exc_info.value)

    async def test_2515(self):
        """Test disabling provider with a large user list."""
        db_users = [f"DB_USER_{i}" for i in range(1000)]
        with pytest.raises(oracledb.DatabaseError):
            await select_ai.async_revoke_http_access(
                users=db_users,
                provider_endpoint=self.provider_endpoint,
            )

    async def test_2516(self):
        """Test disabling provider ACLs for all supported provider endpoints."""
        provider_endpoints = get_supported_provider_endpoints()
        for provider_name, provider_endpoint in provider_endpoints.items():
            if provider_endpoint != self.provider_endpoint:
                await select_ai.async_grant_http_access(
                    users=self.db_users,
                    provider_endpoint=provider_endpoint,
                )
            await select_ai.async_revoke_http_access(
                users=self.db_users,
                provider_endpoint=provider_endpoint,
            )
            logger.info(
                "Provider disabled successfully for %s endpoint %s.",
                provider_name,
                provider_endpoint,
            )

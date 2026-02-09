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

logger = logging.getLogger("TestAsyncEnableProvider")

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="class", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )


@pytest.fixture(scope="class")
def provider_params(request, test_env):
    request.cls.provider_params = {
        "user": test_env.admin_user,
        "password": test_env.admin_password,
        "dsn": test_env.connect_string,
    }


@pytest.fixture(scope="class", autouse=True)
async def setup_and_teardown(request, async_connect, provider_params, test_env):
    logger.info("=== Setting up TestAsyncEnableProvider class ===")
    await select_ai.async_disconnect()
    await select_ai.async_connect(**test_env.connect_params(admin=True))
    assert await select_ai.async_is_connected(), "Connection to DB failed"

    cls = request.cls
    cls.user = cls.provider_params["user"]
    cls.password = cls.provider_params["password"]
    cls.dsn = cls.provider_params["dsn"]
    cls.db_users = []

    try:
        for i in range(1, 6):
            user = f"DB_USER{i}"
            await cls.create_local_user(user)
            cls.db_users.append(user)
    except Exception:
        await select_ai.async_disconnect()
        await select_ai.async_connect(**test_env.connect_params())
        raise

    yield

    logger.info("=== Tearing down TestAsyncEnableProvider class ===")
    async with select_ai.async_cursor() as admin_cursor:
        for user in cls.db_users:
            try:
                await admin_cursor.execute(f"DROP USER {user} CASCADE")
            except oracledb.DatabaseError:
                pass
    try:
        await select_ai.async_disconnect()
    except Exception as exc:
        logger.warning("Warning: disconnect failed (%s)", exc)
    await select_ai.async_connect(**test_env.connect_params())


@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    yield
    logger.info("--- Finished test: %s ---", request.function.__name__)


@pytest.mark.usefixtures("provider_params", "setup_and_teardown")
class TestAsyncEnableProvider:
    @classmethod
    async def create_local_user(cls, test_username="TEST_USER1"):
        test_password = cls.password
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
        self.db_users = self.__class__.db_users

    async def test_2401(self):
        """Test enabling provider with valid users and endpoint."""
        try:
            await select_ai.async_grant_http_access(
                users=self.db_users,
                provider_endpoint=self.provider_endpoint,
            )
            logger.info("Provider enabled successfully for all test users.")
        except Exception as exc:
            pytest.fail(
                f"async_grant_http_access() raised {exc} unexpectedly."
            )

    async def test_2402(self):
        """Test enabling provider with a non-existent username."""
        db_users = ["DB_USER1", "TEST_USER2"]
        with pytest.raises(oracledb.DatabaseError, match=r"ORA-46238") as exc_info:
            await select_ai.async_grant_http_access(
                users=db_users,
                provider_endpoint=self.provider_endpoint,
            )
        logger.info("Expected DatabaseError caught: %s", exc_info.value)
        assert "TEST_USER2" in str(exc_info.value)

    async def test_2403(self):
        """Test enabling provider with all non-existent usernames."""
        db_users = ["TEST_USER1", "TEST_USER2"]
        with pytest.raises(oracledb.DatabaseError, match=r"ORA-46238") as exc_info:
            await select_ai.async_grant_http_access(
                users=db_users,
                provider_endpoint=self.provider_endpoint,
            )
        logger.info("Expected DatabaseError caught: %s", exc_info.value)
        assert "TEST_USER1" in str(exc_info.value)

    async def test_2404(self):
        """Test enabling provider with empty users list."""
        try:
            await select_ai.async_grant_http_access(
                users=[],
                provider_endpoint=self.provider_endpoint,
            )
            logger.info("Provider enabled successfully with empty users.")
        except Exception as exc:
            pytest.fail(
                "async_grant_http_access() raised "
                f"{exc} unexpectedly with empty users."
            )

    async def test_2405(self):
        """Test enabling provider with users as string instead of list."""
        try:
            await select_ai.async_grant_http_access(
                users="DB_USER1",
                provider_endpoint=self.provider_endpoint,
            )
            logger.info("Provider enabled successfully with string user input.")
        except Exception as exc:
            pytest.fail(
                f"async_grant_http_access() raised unexpected exception: {exc}"
            )

    async def test_2406(self):
        """Test enabling provider with users as int - expect TypeError."""
        with pytest.raises(TypeError) as exc_info:
            await select_ai.async_grant_http_access(
                users=2,
                provider_endpoint=self.provider_endpoint,
            )
        logger.info("Expected TypeError caught: %s", exc_info.value)

    async def test_2407(self):
        """Test enabling provider with missing provider_endpoint."""
        with pytest.raises(oracledb.DatabaseError, match=r"ORA-29261") as exc_info:
            await select_ai.async_grant_http_access(
                users=self.db_users,
                provider_endpoint=None,
            )
        logger.info("Expected DatabaseError caught: %s", exc_info.value)

    async def test_2408(self):
        """Test enabling provider with a syntactically valid custom host."""
        try:
            await select_ai.async_grant_http_access(
                users=self.db_users,
                provider_endpoint="invalid.endpoint",
            )
            logger.info("Provider enabled successfully for custom host name.")
        except Exception as exc:
            pytest.fail(
                "async_grant_http_access() raised "
                f"{exc} unexpectedly with custom host name."
            )

    async def test_2409(self):
        """Test enabling provider with duplicate usernames."""
        try:
            await select_ai.async_grant_http_access(
                users=[self.db_users[0], self.db_users[0]],
                provider_endpoint=self.provider_endpoint,
            )
            logger.info("Provider enabled successfully with duplicate users.")
        except Exception as exc:
            pytest.fail(
                "async_grant_http_access() raised "
                f"{exc} unexpectedly with duplicate users."
            )

    async def test_2410(self):
        """Test enabling provider with lowercase username."""
        try:
            await select_ai.async_grant_http_access(
                users=[self.db_users[0].lower()],
                provider_endpoint=self.provider_endpoint,
            )
            logger.info("Provider enabled successfully for lowercase username.")
        except Exception as exc:
            pytest.fail(
                "async_grant_http_access() raised "
                f"{exc} unexpectedly with lowercase username."
            )

    async def test_2411(self):
        """Test enabling provider with username containing whitespace."""
        db_users = [f"  {self.db_users[0]}  "]
        try:
            await select_ai.async_grant_http_access(
                users=db_users,
                provider_endpoint=self.provider_endpoint,
            )
            logger.info("Provider enabled successfully with whitespace user.")
        except Exception as exc:
            pytest.fail(
                "async_grant_http_access() raised "
                f"{exc} unexpectedly with whitespace user."
            )

    async def test_2412(self):
        """Test enabling provider with large user list."""
        db_users = [f"DB_USER_{i}" for i in range(1000)]
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_grant_http_access(
                users=db_users,
                provider_endpoint=self.provider_endpoint,
            )
        logger.info("Expected DatabaseError caught: %s", exc_info.value)

    async def test_2413(self):
        """Test enabling provider with a valid custom endpoint."""
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_grant_http_access(
                users=self.db_users,
                provider_endpoint="https://custom.openai.azure.com",
            )
        logger.info("Expected DatabaseError caught: %s", exc_info.value)
        assert (
            "ORA-24244: invalid host or port for access control list "
            "(ACL) assignment" in str(exc_info.value)
        )

    async def test_2414(self):
        """Test enabling provider ACLs for all supported provider endpoints."""
        provider_endpoints = get_supported_provider_endpoints()
        for provider_name, provider_endpoint in provider_endpoints.items():
            await select_ai.async_grant_http_access(
                users=self.db_users,
                provider_endpoint=provider_endpoint,
            )
            logger.info(
                "Provider enabled successfully for %s endpoint %s.",
                provider_name,
                provider_endpoint,
            )

# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import logging
import uuid

import oracledb
import pytest
import select_ai
from provider.conftest import (
    ensure_provider_test_user_exists,
    get_supported_provider_endpoints,
    grant_provider_test_user_privileges,
)

logger = logging.getLogger("TestDisableProvider")


@pytest.fixture(scope="class", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )


@pytest.fixture(scope="class")
def disable_params(request, test_env):
    params = {
        "user": test_env.admin_user,
        "password": test_env.admin_password,
        "dsn": test_env.connect_string,
    }
    request.cls.disable_params = params


@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown(request, connect, disable_params):
    logger.info("\n=== Setting up TestDisableProvider class ===")
    assert select_ai.is_connected(), "Connection to DB failed"
    cls = request.cls
    cls.user_prefix = f"P2500S_{uuid.uuid4().hex[:8].upper()}"
    cls.db_users = []
    cls.missing_users = [
        f"{cls.user_prefix}_MISS1",
        f"{cls.user_prefix}_MISS2",
    ]
    cls.non_granted_user = f"{cls.user_prefix}_NG"
    try:
        for i in range(1, 6):
            user = f"{cls.user_prefix}_{i}"
            cls.create_local_user(user)
            cls.db_users.append(user)
        cls.create_local_user(cls.non_granted_user)
        logger.info("Setup complete.\n")
        yield
    finally:
        logger.info("\n=== Tearing down TestDisableProvider class ===")
        with select_ai.cursor() as admin_cursor:
            for user in [*cls.db_users, cls.non_granted_user]:
                try:
                    admin_cursor.execute(f"DROP USER {user} CASCADE")
                    logger.info(f"Dropped user {user}")
                except oracledb.DatabaseError as e:
                    logger.warning(f"Disconnect failed: {e}")


@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info(f"--- Starting test: {request.function.__name__} ---")
    yield
    logger.info(f"--- Finished test: {request.function.__name__} ---")


@pytest.mark.usefixtures("disable_params", "setup_and_teardown")
class TestDisableProvider:

    @classmethod
    def create_local_user(cls, test_username):
        logger.info(f"Creating local user: {test_username}")
        test_password = cls.disable_params["password"]
        with select_ai.cursor() as admin_cursor:
            try:
                admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            except oracledb.DatabaseError:
                pass  # Ignore if user doesn't exist
        ensure_provider_test_user_exists(test_username, test_password)
        grant_provider_test_user_privileges(test_username)
        select_ai.grant_privileges(users=[test_username])
        logger.info(f"User {test_username} created successfully.")

    def setup_method(self, method):
        logger.info(f"\n--- Starting test: {method.__name__} ---")
        self.provider_endpoint = "*.openai.azure.com"
        self.db_users = self.__class__.db_users
        self.missing_users = self.__class__.missing_users
        self.non_granted_user = self.__class__.non_granted_user
        self.user_prefix = self.__class__.user_prefix
        try:
            select_ai.grant_http_access(
                users=self.db_users, provider_endpoint=self.provider_endpoint
            )
            logger.info(f"Provider enabled for {len(self.db_users)} users.")
        except Exception as e:
            pytest.fail(f"grant_http_access() raised {e} unexpectedly.")

    def teardown_method(self, method):
        logger.info(f"--- Finished test: {method.__name__} ---")

    # === TEST CASES ===

    def test_2501(self):
        "Test disabling provider with all valid users and endpoint"
        try:
            select_ai.revoke_http_access(
                users=self.db_users, provider_endpoint=self.provider_endpoint
            )
            logger.info("Provider disabled successfully for all valid users.")
        except Exception as e:
            pytest.fail(f"revoke_http_access() raised {e} unexpectedly.")

    def test_2502(self):
        "Test disabling provider with a mix of existing and non-existent usernames"
        db_users = [self.db_users[0], self.missing_users[0]]
        with pytest.raises(oracledb.DatabaseError):
            select_ai.revoke_http_access(
                users=db_users, provider_endpoint=self.provider_endpoint
            )
        logger.info("Caught expected DatabaseError for nonexistent user.")

    def test_2503(self):
        "Test disabling provider with all invalid usernames"
        with pytest.raises(oracledb.DatabaseError):
            select_ai.revoke_http_access(
                users=self.missing_users,
                provider_endpoint=self.provider_endpoint,
            )
        logger.info("Caught expected DatabaseError for invalid users input.")

    def test_2504(self):
        "Test disabling provider with users as integer (TypeError/ValueError expected)"
        with pytest.raises((TypeError, ValueError)):
            select_ai.revoke_http_access(
                users=123, provider_endpoint=self.provider_endpoint
            )
        logger.info(
            "Caught expected TypeError/ValueError for int users input."
        )

    def test_2505(self):
        "Test disabling provider with users as string"
        try:
            select_ai.revoke_http_access(
                users=self.db_users[0],
                provider_endpoint=self.provider_endpoint,
            )
            logger.info(
                "Provider disabled successfully for string user input."
            )
        except Exception as e:
            pytest.fail(f"revoke_http_access() raised {e} unexpectedly.")

    def test_2506(self):
        "Test disabling provider with users as None (TypeError/ValueError expected)"
        with pytest.raises((TypeError, ValueError)):
            select_ai.revoke_http_access(
                users=None, provider_endpoint=self.provider_endpoint
            )
        logger.info(
            "Caught expected TypeError/ValueError for none users input."
        )

    def test_2507(self):
        "Test disabling provider with missing provider_endpoint (ORA-29261 expected)"
        with pytest.raises(
            oracledb.DatabaseError, match=r"ORA-29261: bad argument"
        ):
            select_ai.revoke_http_access(
                users=self.db_users, provider_endpoint=None
            )
        logger.info("Caught expected ORA-29261 for missing endpoint.")

    def test_2508(self):
        "Test disabling provider with invalid endpoint (DatabaseError expected)"
        with pytest.raises(oracledb.DatabaseError):
            select_ai.revoke_http_access(
                users=self.db_users, provider_endpoint="invalid.endpoint"
            )
        logger.info("Caught expected DatabaseError for invalid endpoint.")

    def test_2509(self):
        "Test disabling provider with empty users list"
        try:
            select_ai.revoke_http_access(
                users=[], provider_endpoint=self.provider_endpoint
            )
            logger.info(
                "revoke_http_access() succeeded with empty users list."
            )
        except Exception as e:
            pytest.fail(
                f"revoke_http_access() raised {e} unexpectedly with empty users list."
            )

    def test_2510(self):
        "Test disabling provider with duplicate usernames (ORA-01927 expected)"
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.revoke_http_access(
                users=[self.db_users[0], self.db_users[0]],
                provider_endpoint=self.provider_endpoint,
            )
        assert "ORA-01927" in str(cm.value)
        logger.info("Caught expected ORA-01927 for duplicate users.")

    def test_2511(self):
        "Test disabling provider with lowercase username"
        try:
            select_ai.revoke_http_access(
                users=[self.db_users[0].lower()],
                provider_endpoint=self.provider_endpoint,
            )
            logger.info(
                "revoke_http_access() succeeded with lowercase username."
            )
        except Exception as e:
            pytest.fail(
                f"revoke_http_access() raised {e} unexpectedly with lowercase username."
            )

    def test_2512(self):
        "Test disabling provider with username containing whitespace"
        db_users = [f"  {self.db_users[0]}  "]
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.revoke_http_access(
                users=db_users, provider_endpoint=self.provider_endpoint
            )
        assert "ORA-01927" in str(cm.value)
        logger.info("Caught expected ORA-01927 for whitespace username.")

    def test_2513(self):
        "Test disabling provider with valid custom endpoint (ORA-24244 expected)"
        with pytest.raises(
            oracledb.DatabaseError,
            match=r"ORA-24244: invalid host or port for access control list \(ACL\) assignment",
        ):
            select_ai.revoke_http_access(
                users=self.db_users,
                provider_endpoint="https://custom.openai.azure.com",
            )
        logger.info("Caught expected ORA-24244 for custom endpoint.")

    def test_2514(self):
        "Test disabling provider with non-granted user (ORA-01927 expected)"
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.revoke_http_access(
                users=[self.non_granted_user],
                provider_endpoint=self.provider_endpoint,
            )
        assert "ORA-01927" in str(cm.value)
        logger.info("Caught expected ORA-01927 for non-granted user.")

    def test_2515(self):
        "Test disabling provider with a large user list (DatabaseError expected)"
        db_users = [f"{self.user_prefix}_BULK_{i}" for i in range(1000)]
        with pytest.raises(oracledb.DatabaseError):
            select_ai.revoke_http_access(
                users=db_users, provider_endpoint=self.provider_endpoint
            )
        logger.info("Caught expected DatabaseError for large user list.")

    def test_2516(self):
        "Test disabling provider ACLs for all supported provider endpoints"
        logger.info(
            "Testing revoke_http_access() across supported provider endpoints"
        )
        provider_endpoints = get_supported_provider_endpoints()
        for provider_name, provider_endpoint in provider_endpoints.items():
            if provider_endpoint != self.provider_endpoint:
                select_ai.grant_http_access(
                    users=self.db_users,
                    provider_endpoint=provider_endpoint,
                )
            select_ai.revoke_http_access(
                users=self.db_users,
                provider_endpoint=provider_endpoint,
            )
            logger.info(
                "Provider disabled successfully for %s endpoint %s.",
                provider_name,
                provider_endpoint,
            )

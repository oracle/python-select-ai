# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import logging
import pytest
import select_ai
import test_env
import oracledb

logger = logging.getLogger("TestDisableProvider")

@pytest.fixture(scope="class", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO
    )

@pytest.fixture(scope="class")
def disable_params(request):
    params = {
        "user":         test_env.get_test_user(),
        "password":     test_env.get_test_password(),
        "dsn":          test_env.get_connect_string(),
        "use_wallet":   test_env.get_use_wallet(),
    }
    request.cls.disable_params = params

@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown(request, disable_params):
    logger.info("\n=== Setting up TestDisableProvider class ===")
    test_env.create_connection(use_wallet=request.cls.disable_params["use_wallet"])
    assert select_ai.is_connected(), "Connection to DB failed"
    db_users = []
    for i in range(1, 6):
        user = f"DB_USER{i}"
        request.cls.create_local_user(user)
        db_users.append(user)
    request.cls.db_users = db_users
    # Create Additional user
    request.cls.create_local_user("DB_USER6")
    logger.info("Setup complete.\n")
    yield

    logger.info("\n=== Tearing down TestDisableProvider class ===")
    db_users.append("DB_USER6")
    with select_ai.cursor() as admin_cursor:
        for user in db_users:
            try:
                admin_cursor.execute(f"DROP USER {user} CASCADE")
                logger.info(f"Dropped user {user}")
            except oracledb.DatabaseError as e:
                logger.warning(f"Disconnect failed: {e}")
    try:
        select_ai.disconnect()
    except Exception as e:
        logger.warning(f"Warning: disconnect failed ({e})")

@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info(f"--- Starting test: {request.function.__name__} ---")
    yield
    logger.info(f"--- Finished test: {request.function.__name__} ---")

@pytest.mark.usefixtures("disable_params", "setup_and_teardown")
class TestDisableProvider:

    @classmethod
    def create_local_user(cls, test_username="TEST_USER1"):
        logger.info(f"Creating local user: {test_username}")
        test_password = cls.disable_params["password"]
        with select_ai.cursor() as admin_cursor:
            try:
                admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            except oracledb.DatabaseError:
                pass  # Ignore if user doesn't exist
            admin_cursor.execute(f"CREATE USER {test_username} IDENTIFIED BY {test_password}")
            admin_cursor.execute(f"grant create session, create table, unlimited tablespace to {test_username}")
            admin_cursor.execute(f"grant execute on dbms_cloud to {test_username}")
        logger.info(f"User {test_username} created successfully.")

    def setup_method(self, method):
        logger.info(f"\n--- Starting test: {method.__name__} ---")
        self.provider_endpoint = "*.openai.azure.com"
        try:
            select_ai.enable_provider(
                users=self.db_users,
                provider_endpoint=self.provider_endpoint
            )
            logger.info(f"Provider enabled for {len(self.db_users)} users.")
        except Exception as e:
            pytest.fail(f"enable_provider() raised {e} unexpectedly.")

    def teardown_method(self, method):
        logger.info(f"--- Finished test: {method.__name__} ---")

    # === TEST CASES ===

    def test_2501(self):
        "Test disabling provider with all valid users and endpoint"
        try:
            select_ai.disable_provider(
                users=self.db_users,
                provider_endpoint=self.provider_endpoint
            )
            logger.info("Provider disabled successfully for all valid users.")
        except Exception as e:
            pytest.fail(f"disable_provider() raised {e} unexpectedly.")

    def test_2502(self):
        "Test disabling provider with a mix of existing and non-existent usernames"
        db_users = ["DB_USER1", "TEST_USER2"]
        with pytest.raises(oracledb.DatabaseError):
            select_ai.disable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )
        logger.info("Caught expected DatabaseError for nonexistent user.")

    def test_2503(self):
        "Test disabling provider with all invalid usernames"
        with pytest.raises(oracledb.DatabaseError):
            select_ai.disable_provider(
                users=["INVALID_USER1", "INVALID_USER2"],
                provider_endpoint=self.provider_endpoint
            )
        logger.info("Caught expected DatabaseError for invalid users input.")

    def test_2504(self):
        "Test disabling provider with users as integer (TypeError/ValueError expected)"
        with pytest.raises((TypeError, ValueError)):
            select_ai.disable_provider(
                users=123,
                provider_endpoint=self.provider_endpoint
            )
        logger.info("Caught expected TypeError/ValueError for int users input.")

    def test_2505(self):
        "Test disabling provider with users as string"
        try:
            select_ai.disable_provider(
                users="DB_USER1",
                provider_endpoint=self.provider_endpoint
            )
            logger.info("Provider disabled successfully for string user input.")
        except Exception as e:
            pytest.fail(f"disable_provider() raised {e} unexpectedly.")

    def test_2506(self):
        "Test disabling provider with users as None (TypeError/ValueError expected)"
        with pytest.raises((TypeError, ValueError)):
            select_ai.disable_provider(
                users=None,
                provider_endpoint=self.provider_endpoint
            )
        logger.info("Caught expected TypeError/ValueError for none users input.")

    def test_2507(self):
        "Test disabling provider with missing provider_endpoint (ValueError expected)"
        with pytest.raises(ValueError):
            select_ai.disable_provider(
                users=self.db_users,
                provider_endpoint=None
            )
        logger.info("Caught expected ValueError for missing endpoint.")

    def test_2508(self):
        "Test disabling provider with invalid endpoint (DatabaseError expected)"
        with pytest.raises(oracledb.DatabaseError):
            select_ai.disable_provider(
                users=self.db_users,
                provider_endpoint="invalid.endpoint"
            )
        logger.info("Caught expected DatabaseError for invalid endpoint.")

    def test_2509(self):
        "Test disabling provider with empty users list"
        try:
            select_ai.disable_provider(
                users=[],
                provider_endpoint=self.provider_endpoint
            )
            logger.info("disable_provider() succeeded with empty users list.")
        except Exception as e:
            pytest.fail(f"disable_provider() raised {e} unexpectedly with empty users list.")

    def test_2510(self):
        "Test disabling provider with duplicate usernames (ORA-01927 expected)"
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.disable_provider(
                users=[self.db_users[0], self.db_users[0]],
                provider_endpoint=self.provider_endpoint
            )
        assert "ORA-01927" in str(cm.value)
        logger.info("Caught expected ORA-01927 for duplicate users.")

    def test_2511(self):
        "Test disabling provider with lowercase username"
        try:
            select_ai.disable_provider(
                users=[self.db_users[0].lower()],
                provider_endpoint=self.provider_endpoint
            )
            logger.info("disable_provider() succeeded with lowercase username.")
        except Exception as e:
            pytest.fail(f"disable_provider() raised {e} unexpectedly with lowercase username.")

    def test_2512(self):
        "Test disabling provider with username containing whitespace"
        db_users = [f"  {self.db_users[0]}  "]
        try:
            select_ai.disable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )
            logger.info("disable_provider() succeeded with whitespace username.")
        except Exception as e:
            pytest.fail(f"disable_provider() raised {e} unexpectedly with whitespace in username.")

    def test_2513(self):
        "Test disabling provider with valid custom endpoint (ORA-24244 expected)"
        with pytest.raises(
            oracledb.DatabaseError,
            match=r"ORA-24244: invalid host or port for access control list \(ACL\) assignment"
        ):
            select_ai.disable_provider(
                users=self.db_users,
                provider_endpoint="https://custom.openai.azure.com"
            )
        logger.info("Caught expected ORA-24244 for custom endpoint.")

    def test_2514(self):
        "Test disabling provider with non-granted user (ORA-01927 expected)"
        non_granted_user = "DB_USER6"
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.disable_provider(
                users=[non_granted_user],
                provider_endpoint=self.provider_endpoint
            )
        assert "ORA-01927" in str(cm.value)
        logger.info("Caught expected ORA-01927 for non-granted user.")

    def test_2515(self):
        "Test disabling provider with a large user list (DatabaseError expected)"
        db_users = [f"DB_USER_{i}" for i in range(1000)]
        with pytest.raises(oracledb.DatabaseError):
            select_ai.disable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )
        logger.info("Caught expected DatabaseError for large user list.")
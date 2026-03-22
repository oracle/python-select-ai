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

logger = logging.getLogger("TestEnableProvider")

@pytest.fixture(scope="class", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO
    )

@pytest.fixture(scope="class")
def provider_params(request):
    params = {
        "user":       test_env.get_test_user(),
        "password":   test_env.get_test_password(),
        "dsn":        test_env.get_connect_string(),
    }
    request.cls.provider_params = params

@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown(request, provider_params):
    logger.info("=== Setting up TestEnableProvider class ===")
    test_env.create_connection()
    assert select_ai.is_connected(), "Connection to DB failed"
    cls = request.cls
    cls.user = cls.provider_params["user"]
    cls.password = cls.provider_params["password"]
    cls.dsn = cls.provider_params["dsn"]
    cls.db_users = []
    # Create multiple DB users (DB_USER1 ... DB_USER5)
    for i in range(1, 6):
        user = f"DB_USER{i}"
        cls.create_local_user(user)
        cls.db_users.append(user)
    yield
    logger.info("=== Tearing down TestEnableProvider class ===")
    # Drop DB users
    with select_ai.cursor() as admin_cursor:
        for user in cls.db_users:
            try:
                admin_cursor.execute(f"DROP USER {user} CASCADE")
            except oracledb.DatabaseError:
                pass  # Ignore if already dropped
    try:
        select_ai.disconnect()
    except Exception as e:
        logger.warning(f"Warning: disconnect failed ({e})")

@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info(f"--- Starting test: {request.function.__name__} ---")
    yield
    logger.info(f"--- Finished test: {request.function.__name__} ---")

@pytest.mark.usefixtures("provider_params", "setup_and_teardown")
class TestEnableProvider:
    @classmethod
    def create_local_user(cls, test_username="TEST_USER1"):
        test_password = cls.password
        with select_ai.cursor() as admin_cursor:
            try:
                admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            except oracledb.DatabaseError:
                pass
            admin_cursor.execute(f"CREATE USER {test_username} IDENTIFIED BY {test_password}")
            admin_cursor.execute(f"grant create session, create table, unlimited tablespace to {test_username}")
            admin_cursor.execute(f"grant execute on dbms_cloud to {test_username}")

    def setup_method(self, method):
        logger.info(f"SetUp for {method.__name__}")
        self.provider_endpoint = "*.openai.azure.com"
        self.db_users = self.__class__.db_users

    # ---- TESTS ----

    def test_2401(self):
        "Test enabling provider with valid users and endpoint"
        logger.info("Testing enable_provider() with valid users and valid endpoint")
        try:
            select_ai.enable_provider(
                users=self.db_users,
                provider_endpoint=self.provider_endpoint
            )
            logger.info("Provider enabled successfully for all test users.")
        except Exception as e:
            logger.error(f"enable_provider() raised {e} unexpectedly.")
            pytest.fail(f"enable_provider() raised {e} unexpectedly.")

    def test_2402(self):
        "Test enabling provider with a non-existent username"
        logger.info("Testing enable_provider() with a mix of existing and non-existent usernames")
        db_users = ["DB_USER1", "TEST_USER2"]
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.enable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )
        logger.info(f"Expected DatabaseError caught: {cm.value}")
        assert "ORA-01917: user or role 'TEST_USER2' does not exist" in str(cm.value)
        logger.info("Test for non-existent username completed.")

    def test_2403(self):
        "Test enabling provider with all non-existent usernames"
        logger.info("Testing enable_provider() with all non-existent usernames")
        db_users = ["TEST_USER1", "TEST_USER2"]
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.enable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )
        logger.info(f"Expected DatabaseError caught: {cm.value}")
        assert "ORA-01917: user or role 'TEST_USER1' does not exist" in str(cm.value)
        logger.info("Test for all non-existent usernames completed.")

    def test_2404(self):
        "Test enabling provider with empty users list"
        logger.info("Testing enable_provider() with empty users list")
        try:
            select_ai.enable_provider(
                users=[],
                provider_endpoint=self.provider_endpoint
            )
            logger.info("Provider enabled successfully with empty users (expected and allowed).")
        except Exception as e:
            logger.error(f"enable_provider() raised {e} unexpectedly with empty users.")
            pytest.fail(f"enable_provider() raised {e} unexpectedly with empty users.")

    def test_2405(self):
        "Test enabling provider with users as string instead of list"
        logger.info("Testing enable_provider() with users as a string (should be list; verify no TypeError is raised)")
        try:
            select_ai.enable_provider(
                users="DB_USER1",   # not a list
                provider_endpoint=self.provider_endpoint
            )
            logger.info("No TypeError raised. Library may accept strings for 'users'.")
        except Exception as e:
            logger.warning(f"Unexpected exception caught: {e}")
            pytest.fail(f"enable_provider() raised unexpected exception: {e}")

    def test_2406(self):
        "Test enabling provider with users as int - expect TypeError"
        logger.info("Testing enable_provider() with users as an integer (type error expected)")
        with pytest.raises(TypeError) as cm:
            select_ai.enable_provider(
                users=2,   # not a list
                provider_endpoint=self.provider_endpoint
            )
        logger.info(f"Expected TypeError caught: {cm.value}")

    def test_2407(self):
        "Test enabling provider with missing provider_endpoint"
        logger.info("Testing enable_provider() with None as provider_endpoint (ValueError expected)")
        with pytest.raises(ValueError) as cm:
            select_ai.enable_provider(
                users=self.db_users,
                provider_endpoint=None
            )
        logger.info(f"Expected ValueError caught: {cm.value}")

    def test_2408(self):
        "Test enabling provider with invalid endpoint"
        logger.info("Testing enable_provider() with an invalid endpoint (ValueError expected)")
        with pytest.raises(ValueError) as cm:
            select_ai.enable_provider(
                users=self.db_users,
                provider_endpoint="invalid.endpoint"
            )
        logger.info(f"Expected ValueError caught: {cm.value}")

    def test_2409(self):
        "Test enabling provider with duplicate usernames"
        logger.info("Testing enable_provider() with duplicate usernames")
        try:
            select_ai.enable_provider(
                users=[self.db_users[0], self.db_users[0]],
                provider_endpoint=self.provider_endpoint
            )
            logger.info("Provider enabled successfully with duplicate users (expected and allowed).")
        except Exception as e:
            logger.error(f"enable_provider() raised {e} unexpectedly with duplicate users.")
            pytest.fail(f"enable_provider() raised {e} unexpectedly with duplicate users.")

    def test_2410(self):
        "Test enabling provider with lowercase username (case-insensitive)"
        logger.info("Testing enable_provider() with username in lowercase (should succeed on case-insensitive DB)")
        try:
            select_ai.enable_provider(
                users=[self.db_users[0].lower()],
                provider_endpoint=self.provider_endpoint
            )
            logger.info("Provider enabled successfully for lowercase username.")
        except Exception as e:
            logger.error(f"enable_provider() raised {e} unexpectedly with lowercase username.")
            pytest.fail(f"enable_provider() raised {e} unexpectedly with lowercase username.")

    def test_2411(self):
        "Test enabling provider with username containing whitespace"
        logger.info("Testing enable_provider() with username containing leading/trailing whitespace")
        db_users = [f"  {self.db_users[0]}  "]
        try:
            select_ai.enable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )
            logger.info("Provider enabled successfully with username containing whitespace.")
        except Exception as e:
            logger.error(f"enable_provider() raised {e} unexpectedly with whitespace in username.")
            pytest.fail(f"enable_provider() raised {e} unexpectedly with whitespace in username.")

    def test_2412(self):
        "Test enabling provider with large user list"
        logger.info("Testing enable_provider() with a very large list of users (DatabaseError expected)")
        db_users = [f"DB_USER_{i}" for i in range(1000)]
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.enable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )
        logger.info(f"Expected DatabaseError caught: {cm.value}")

    def test_2413(self):
        "Test enabling provider with a valid custom endpoint (ORA-24244 expected)"
        logger.info("Testing enable_provider() with a custom endpoint (ORA-24244 expected)")
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.enable_provider(
                users=self.db_users,
                provider_endpoint="https://custom.openai.azure.com"
            )
        logger.info(f"Expected DatabaseError caught: {cm.value}")
        assert "ORA-24244: invalid host or port for access control list (ACL) assignment" in str(cm.value)
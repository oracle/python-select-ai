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

from select_ai.errors import DatabaseNotConnectedError

logger = logging.getLogger("TestDropCredential")

@pytest.fixture(scope="class", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO
    )

@pytest.fixture(scope="class")
def drop_params(request):
    params = {
        "user":             test_env.get_test_user(),
        "password":         test_env.get_test_password(),
        "dsn":              test_env.get_connect_string(),
        "use_wallet":       test_env.get_use_wallet(),
        "cred_username":    test_env.get_cred_username(),
        "cred_password":    test_env.get_cred_password(),
    }
    request.cls.drop_params = params

@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown(request, drop_params):
    logger.info("=== Setting up TestDropCredential class ===")
    test_env.create_connection(use_wallet=request.cls.drop_params["use_wallet"])
    assert select_ai.is_connected(), "Connection to DB failed"
    logger.info("Initial connection successful")
    yield
    logger.info("=== Tearing down TestDropCredential class ===")
    try:
        select_ai.disconnect()
        logger.info("Disconnected from DB")
    except Exception as e:
        logger.warning(f"Warning: disconnect failed ({e})")

@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info(f"--- Starting test: {request.function.__name__} ---")
    yield
    logger.info(f"--- Finished test: {request.function.__name__} ---")

@pytest.mark.usefixtures("drop_params", "setup_and_teardown")
class TestDropCredential:
    @staticmethod
    def get_cred_param(params, cred_name=None):
        logger.info(f"Preparing credential params for: {cred_name}")
        return dict(
            credential_name = cred_name,
            username        = params["cred_username"],
            password        = params["cred_password"]
        )
    @classmethod
    def create_test_credential(cls, cred_name="GENAI_CRED"):
        logger.info(f"Creating test credential: {cred_name}")
        credential = cls.get_cred_param(cls.drop_params, cred_name)
        try:
            select_ai.create_credential(credential=credential, replace=False)
            logger.info(f"Credential '{cred_name}' created successfully.")
        except Exception as e:
            pytest.fail(f"create_credential() raised {e} unexpectedly.")
    @classmethod
    def create_local_user(cls, test_username="TEST_USER1"):
        logger.info(f"Creating local user: {test_username}")
        test_password = cls.drop_params["password"]
        with select_ai.cursor() as admin_cursor:
            try:
                admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            except oracledb.DatabaseError:
                pass  # Ignore if user doesn't exist
            admin_cursor.execute(f"CREATE USER {test_username} IDENTIFIED BY {test_password}")
            admin_cursor.execute(f"grant create session, create table, unlimited tablespace to {test_username}")
            admin_cursor.execute(f"grant execute on dbms_cloud to {test_username}")
        logger.info(f"Local user '{test_username}' ready.")

    def test_2301(self):
        """Deleting existing credential (force=True)"""
        logger.info("Deleting existing credential (force=True)")
        self.create_test_credential()
        try:
            select_ai.delete_credential("GENAI_CRED", force=True)
            logger.info("Credential deleted successfully.")
        except Exception as e:
            pytest.fail(f"delete_credential() raised {e} unexpectedly.")

    def test_2302(self):
        """Deleting same credential twice (force=True)"""
        logger.info("Deleting same credential twice (force=True)")
        self.create_test_credential()
        select_ai.delete_credential("GENAI_CRED", force=True)
        select_ai.delete_credential("GENAI_CRED", force=True)
        logger.info("Double deletion succeeded (force=True).")

    def test_2303(self):
        """Deleting same credential twice (force=False)"""
        logger.info("Deleting same credential twice (force=False)")
        self.create_test_credential()
        select_ai.delete_credential("GENAI_CRED", force=False)
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.delete_credential("GENAI_CRED", force=False)
        logger.info(f"Expected DatabaseError for second delete (force=False): {cm.value}")

    def test_2304(self):
        """Deleting nonexistent credential (default force=False)"""
        logger.info("Deleting nonexistent credential (default force=False)")
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.delete_credential("nonexistent_cred")
        logger.info(f"Expected DatabaseError for nonexistent credential: {cm.value}")

    def test_2305(self):
        """Deleting nonexistent credential (force=False)"""
        logger.info("Deleting nonexistent credential (force=False)")
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.delete_credential("nonexistent_cred", force=False)
        logger.info(f"Expected DatabaseError for nonexistent credential: {cm.value}")

    def test_2306(self):
        """Deleting nonexistent credential (force=True)"""
        logger.info("Deleting nonexistent credential (force=True)")
        try:
            select_ai.delete_credential("nonexistent_cred", force=True)
            logger.info("No error raised (expected behavior).")
        except Exception as e:
            pytest.fail(f"delete_credential(force=True) raised {e} unexpectedly.")

    def test_2307(self):
        """Deleting credential as local user"""
        logger.info("Deleting credential as local user")
        test_username = "TEST_USER1"
        self.create_local_user(test_username)
        test_env.create_connection(
            user=test_username,
            password=self.drop_params["password"],
            use_wallet=self.drop_params["use_wallet"]
        )
        credential = self.get_cred_param(self.drop_params, "GENAI_CRED_USER1")
        try:
            select_ai.delete_credential("GENAI_CRED_USER1", force=True)
            logger.info("Local user credential deleted successfully.")
        except Exception as e:
            pytest.fail(f"delete_credential() raised {e} unexpectedly.")
        finally:
            select_ai.disconnect()
            test_env.create_connection(use_wallet=self.drop_params["use_wallet"])
            with select_ai.cursor() as admin_cursor:
                admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            logger.info("Local user cleanup complete.")

    def test_2308(self):
        """Deleting credential with invalid name"""
        logger.info("Deleting credential with invalid name")
        with pytest.raises(oracledb.DatabaseError, match=r"ORA-20010: Invalid credential name"):
            select_ai.delete_credential("invalid!@#", force=True)
        logger.info("Caught expected ORA-20010 for invalid name.")

    def test_2309(self):
        """Deleting credential without active connection"""
        logger.info("Deleting credential without active connection")
        select_ai.disconnect()
        with pytest.raises(select_ai.errors.DatabaseNotConnectedError) as cm:
            select_ai.delete_credential("GENAI_CRED", force=True)
        logger.info(f"Expected DatabaseNotConnectedError raised: {cm.value}")

    def test_2310(self):
        """Deleting credential with name exceeding max length"""
        logger.info("Deleting credential with name exceeding max length")
        test_env.create_connection(use_wallet=self.drop_params["use_wallet"])
        long_name = "GENAI_CRED_" + "a" * 120
        with pytest.raises(
            oracledb.DatabaseError,
            match=r"ORA-20008: Credential name length .* exceeds maximum length"
        ):
            select_ai.delete_credential(long_name, force=True)
        logger.info("Caught expected ORA-20008 for long credential name.")

    def test_2311(self):
        """Deleting credential with lowercase name"""
        logger.info("Deleting credential with lowercase name")
        self.create_test_credential("GENAI_CRED")
        try:
            select_ai.delete_credential(credential_name="genai_cred")
            logger.info("Credential deleted successfully (case-insensitive).")
        except Exception as e:
            pytest.fail(f"async_delete_credential raised {e} unexpectedly for lowercase name")

    def test_2312(self):
        """Deleting credential with empty or None name"""
        logger.info("Deleting credential with empty or None name")
        with pytest.raises(oracledb.DatabaseError, match=r"ORA-20010: Missing credential name"):
            select_ai.delete_credential(credential_name="", force=True)
        with pytest.raises(oracledb.DatabaseError, match=r"ORA-20010: Missing credential name"):
            select_ai.delete_credential(credential_name=None, force=True)
        logger.info("Caught expected ORA-20010 for missing credential name.")
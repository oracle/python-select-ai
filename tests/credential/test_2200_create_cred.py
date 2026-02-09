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

logger = logging.getLogger("TestCreateCredential")

@pytest.fixture(scope="class", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO
    )

@pytest.fixture(scope="class")
def credential_params(request):
    params = {
        "user":                 test_env.get_test_user(),
        "password":             test_env.get_test_password(),
        "dsn":                  test_env.get_connect_string(),
        "use_wallet":           test_env.get_use_wallet(),
        "user_ocid":            test_env.get_user_ocid(),
        "tenancy_ocid":         test_env.get_tenancy_ocid(),
        "private_key":          test_env.get_private_key(),
        "fingerprint":          test_env.get_fingerprint(),
        "cred_username":        test_env.get_cred_username(),
        "cred_password":        test_env.get_cred_password(),
    }
    request.cls.credential_params = params

@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown_cred(request, credential_params):
    logger.info("=== Setting up TestCreateCredential class  ===")
    test_env.create_connection(use_wallet=request.cls.credential_params["use_wallet"])
    assert select_ai.is_connected(), "Connection to DB failed"
    logger.info("Initial connection successful")
    yield
    logger.info("=== Tearing down TestCreateCredential class ===")
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

@pytest.mark.usefixtures("credential_params", "setup_and_teardown_cred")
class TestCreateCredential:
    def __init__(self):
        self.logger = logging.getLogger("TestCreateCredential")

    @staticmethod
    def get_native_cred_param(params, cred_name=None):
        return dict(
            credential_name = cred_name,
            user_ocid       = params["user_ocid"],
            tenancy_ocid    = params["tenancy_ocid"],
            private_key     = params["private_key"],
            fingerprint     = params["fingerprint"]
        )
    @staticmethod
    def get_cred_param(params, cred_name=None):
        return dict(
            credential_name = cred_name,
            username        = params["cred_username"],
            password        = params["cred_password"]
        )
    @staticmethod
    def drop_credential_cursor(cursor, cred_name='GENAI_CRED'):
        logger.info(f"Dropping credential: {cred_name}")
        cursor.callproc(
            "DBMS_CLOUD.DROP_CREDENTIAL",
            keyword_parameters={
                "credential_name": cred_name
            },
        )
        logger.info(f"Dropped credential: {cred_name}")

    def test_2201(self):
        """Testing basic credential creation"""
        credential = self.get_cred_param(self.credential_params, 'GENAI_CRED')
        self.logger.info(f"Creating credential: {credential}")
        try:
            select_ai.create_credential(credential=credential, replace=False)
            self.logger.info("Credential created successfully.")
        except Exception as e:
            pytest.fail(f"create_credential() raised {e} unexpectedly.")
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    def test_2202(self):
        """Testing creating credential twice without replace"""
        credential = self.get_cred_param(self.credential_params, 'GENAI_CRED')
        try:
            select_ai.create_credential(credential=credential)
            self.logger.info("First credential creation successful.")
        except Exception as e:
            pytest.fail(f"create_credential() raised {e} unexpectedly.")
        self.logger.info("Attempting to create credential again (expected to fail)...")
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.create_credential(credential=credential)
        self.logger.info(f"Caught expected DatabaseError: {cm.value}")
        assert "ORA-20022" in str(cm.value)
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    def test_2203(self):
        """Testing repeated credential creation with replace=True"""
        credential = self.get_cred_param(self.credential_params, 'GENAI_CRED')
        for i in range(5):
            self.logger.info(f"Creating credential iteration {i+1}...")
            select_ai.create_credential(credential=credential, replace=True)
        self.logger.info("Repeated creation succeeded.")
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    def test_2204(self):
        """Testing credential creation with replace=True"""
        credential = self.get_cred_param(self.credential_params, 'GENAI_CRED')
        try:
            select_ai.create_credential(credential=credential, replace=True)
            self.logger.info("Credential created successfully with replace=True.")
        except Exception as e:
            pytest.fail(f"create_credential() raised {e} unexpectedly.")
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    def test_2205(self):
        """Testing credential creation twice with replace=True"""
        credential = self.get_cred_param(self.credential_params, 'GENAI_CRED')
        try:
            select_ai.create_credential(credential=credential, replace=True)
            self.logger.info("Credential created successfully with replace=True.")
        except Exception as e:
            pytest.fail(f"create_credential() raised {e} unexpectedly.")
        try:
            select_ai.create_credential(credential=credential, replace=True)
            self.logger.info("Credential created successfully with replace=True.")
        except Exception as e:
            pytest.fail(f"create_credential() raised {e} unexpectedly.")
        assert True, "Credential creation and replacement passed without exception."
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    def test_2206(self):
        """Testing replace=True then replace=False behavior"""
        credential = self.get_cred_param(self.credential_params, 'GENAI_CRED')
        try:
            select_ai.create_credential(credential=credential, replace=True)
            self.logger.info("First creation succeeded.")
        except Exception as e:
            pytest.fail(f"create_credential() raised {e} unexpectedly.")
        self.logger.info("Second creation without replace (expected to fail)...")
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.create_credential(credential=credential)
        self.logger.info(f"Caught expected error: {cm.value}")
        assert "ORA-20022" in str(cm.value)
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    def test_2207(self):
        """Testing replace=False followed by replace=True"""
        credential = self.get_cred_param(self.credential_params, 'GENAI_CRED')
        try:
            select_ai.create_credential(credential=credential)
            self.logger.info("Credential created (replace=False).")
        except Exception as e:
            pytest.fail(f"create_credential() raised {e} unexpectedly.")
        try:
            select_ai.create_credential(credential=credential, replace=True)
            self.logger.info("Credential replaced successfully (replace=True).")
        except Exception as e:
            pytest.fail(f"create_credential() raised {e} unexpectedly.")
        assert True, "Credential creation and replacement passed without exception."
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    def test_2208(self):
        """Testing native credential creation"""
        credential = self.get_native_cred_param(self.credential_params, 'GENAI_CRED')
        try:
            select_ai.create_credential(credential=credential, replace=False)
            self.logger.info("Native credential created successfully.")
        except Exception as e:
            pytest.fail(f"create_credential() raised {e} unexpectedly.")
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    def test_2209(self):
        """Testing native credential creation twice"""
        credential = self.get_native_cred_param(self.credential_params, 'GENAI_CRED')
        try:
            select_ai.create_credential(credential=credential)
            self.logger.info("First native credential created.")
        except Exception as e:
            pytest.fail(f"create_credential() raised {e} unexpectedly.")
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.create_credential(credential=credential)
        self.logger.info(f"Expected error caught: {cm.value}")
        assert "ORA-20022" in str(cm.value)
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    def test_2210(self):
        """Testing native credential creation with replace=True"""
        credential = self.get_native_cred_param(self.credential_params, 'GENAI_CRED')
        try:
            select_ai.create_credential(credential=credential, replace=True)
            self.logger.info("Native credential created successfully.")
        except Exception as e:
            pytest.fail(f"create_credential() raised {e} unexpectedly.")
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    def test_2211(self):
        """Testing native credential creation with replace=True twice"""
        credential = self.get_native_cred_param(self.credential_params, 'GENAI_CRED')
        for i in range(2):
            self.logger.info(f"Creating native credential iteration {i+1} (replace=True)...")
            select_ai.create_credential(credential=credential, replace=True)
        self.logger.info("Native credential replaced successfully twice.")
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    def test_2212(self):
        """Testing creation with empty credential name"""
        credential = self.get_cred_param(self.credential_params)
        with pytest.raises(Exception) as cm:
            select_ai.create_credential(credential=credential)
        self.logger.info(f"Expected exception caught: {cm.value}")
        assert "ORA-20010: Missing credential name" in str(cm.value)

    def test_2213(self):
        """Testing credential creation with empty dictionary"""
        credential = dict()
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.create_credential(credential=credential)
        self.logger.info(f"Expected exception caught: {cm.value}")
        assert (
            "PLS-00306: wrong number or types of arguments in call to 'CREATE_CREDENTIAL'" in str(cm.value)
        )

    def test_2214(self):
        """Testing credential creation with invalid username"""
        credential = dict(
            credential_name = 'GENAI_CRED',
            username        = 'invalid_username',
            password        = self.credential_params["cred_password"]
        )
        select_ai.create_credential(credential=credential, replace=True)
        self.logger.info("Credential with invalid username created successfully.")
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    def test_2215(self):
        """Testing credential creation with invalid password"""
        credential = dict(
            credential_name = 'GENAI_CRED',
            username        = self.credential_params["cred_username"],
            password        = 'invalid_pwd'
        )
        select_ai.create_credential(credential=credential, replace=True)
        self.logger.info("Credential with invalid password created successfully.")
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    def test_2216(self):
        """Testing credential creation when DB is disconnected"""
        select_ai.disconnect()
        credential = self.get_cred_param(self.credential_params, 'GENAI_CRED')
        with pytest.raises(DatabaseNotConnectedError):
            select_ai.create_credential(credential=credential, replace=False)
        self.logger.info("Expected DatabaseNotConnectedError raised.")

    def test_2217(self):
        """Test Credential creation for a local test user"""
        self.logger.info("Connecting as admin user...")
        test_env.create_connection(use_wallet=self.credential_params["use_wallet"])
        self.logger.info("Admin connection established.")
        test_username = "TEST_USER1"
        test_password = self.credential_params["password"]
        self.logger.info(f"Ensuring test user '{test_username}' does not exist...")
        with select_ai.cursor() as admin_cursor:
            try:
                admin_cursor.execute(f"DROP USER {test_username} CASCADE")
                self.logger.info(f"Existing user '{test_username}' dropped.")
            except oracledb.DatabaseError:
                self.logger.info(f"User '{test_username}' did not exist, continuing...")
            self.logger.info(f"Creating test user '{test_username}'...")
            admin_cursor.execute(f"CREATE USER {test_username} IDENTIFIED BY {test_password}")
            admin_cursor.execute(f"grant create session, create table, unlimited tablespace to {test_username}")
            admin_cursor.execute(f"grant execute on dbms_cloud to {test_username}")
            self.logger.info(f"User '{test_username}' created and granted privileges.")
        self.logger.info(f"Connecting as test user '{test_username}'...")
        test_env.create_connection(
            user=test_username,
            password=test_password,
            use_wallet=self.credential_params["use_wallet"]
        )
        self.logger.info("Test user connection established.")
        credential = self.get_cred_param(self.credential_params, 'GENAI_CRED_USER1')
        self.logger.info(f"Creating credential '{credential['credential_name']}' for test user...")
        try:
            select_ai.create_credential(credential=credential, replace=False)
            self.logger.info("Credential created successfully.")
        except Exception as e:
            pytest.fail(f"create_credential() raised {e} unexpectedly.")
        self.logger.info(f"Dropping credential '{credential['credential_name']}'...")
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor, 'GENAI_CRED_USER1')
        self.logger.info("Credential dropped.")
        self.logger.info("Disconnecting test user...")
        select_ai.disconnect()
        self.logger.info("Disconnected test user.")
        self.logger.info(f"Reconnecting as admin to drop test user '{test_username}'...")
        test_env.create_connection(use_wallet=self.credential_params["use_wallet"])
        with select_ai.cursor() as admin_cursor:
            admin_cursor.execute(f"DROP USER {test_username} CASCADE")
        self.logger.info(f"Test user '{test_username}' dropped successfully.")

    def test_2218(self):
        """Testing credential name with special characters"""
        credential = self.get_cred_param(self.credential_params, 'GENAI_CRED!@#')
        with pytest.raises(oracledb.DatabaseError, match="ORA-20010: Invalid credential name"):
            select_ai.create_credential(credential=credential, replace=False)
        self.logger.info("Invalid name test passed.")

    def test_2219(self):
        """Testing credential name exceeding 128 characters"""
        long_name = "GENAI_CRED" + "_" + "a" * (128 - len('GENAI_CRED'))
        credential = self.get_cred_param(self.credential_params, long_name)
        with pytest.raises(
            oracledb.DatabaseError,
            match=r"ORA-20008: Credential name length \(129\) exceeds maximum length \(128\)"
        ):
            select_ai.create_credential(credential=credential, replace=False)
        self.logger.info("Long credential name test passed.")

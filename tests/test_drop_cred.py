import unittest
import select_ai
import test_env
import oracledb
import os
import time


class TestDropCredential(unittest.TestCase):
    def setUp(self):
        """
        Setup connection parameters.
        """
        self.user = test_env.get_test_user()
        self.password = test_env.get_test_password()
        self.dsn = test_env.get_localhost_connect_string()

        # Get basic cred secrets
        self.cred_username = test_env.get_cred_username()
        self.cred_password = test_env.get_cred_password()

        # Create connection
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")
    
    def tearDown(self):
        # Disconnect after each test
        select_ai.disconnect()
    

    def get_cred_param(self, cred_name=None) -> dict:
        return dict(
            credential_name = cred_name,
            username        = self.cred_username,
            password        = self.cred_password
        )

    def create_test_credential(self, cred_name="GENAI_CRED"):
        """
        Helper to create a test credential.
        """
        # Get credential secret
        credential = self.get_cred_param(cred_name)

        try:
            select_ai.create_credential(credential=credential, replace=False)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
    

    def create_local_user(self, test_username="TEST_USER1"):
        """
        Helper to drop and create a local test user with required grants.
        """
        test_password = self.password

        # Drop user if exists and create new one
        with select_ai.cursor() as admin_cursor:
            try:
                admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            except oracledb.DatabaseError:
                pass  # Ignore if user doesn't exist

            admin_cursor.execute(f"CREATE USER {test_username} IDENTIFIED BY {test_password}")
            admin_cursor.execute(f"grant create session, create table, unlimited tablespace to {test_username}")
            admin_cursor.execute(f"grant execute on dbms_cloud to {test_username}")


    def test_delete_cred_success(self):
        # Create credential
        self.create_test_credential()

        try:
            select_ai.delete_credential("GENAI_CRED", force=True)
        except Exception as e:
            self.fail(f"delete_credential() raised {e} unexpectedly.")
    
    
    def test_delete_cred_twice_force_true(self):
        # Create credential
        self.create_test_credential()

        # First delete should succeed
        select_ai.delete_credential("GENAI_CRED", force=True)

        # Second delete should also succeed (no exception, since force=True)
        select_ai.delete_credential("GENAI_CRED", force=True)

    
    def test_delete_cred_twice_force_false(self):
        # Create credential
        self.create_test_credential()

        # First delete should succeed
        select_ai.delete_credential("GENAI_CRED", force=False)

        # Second delete should raise DatabaseError since credential is already deleted
        with self.assertRaises(oracledb.DatabaseError):
            select_ai.delete_credential("GENAI_CRED", force=False)
    

    def test_delete_nonexistent_cred_default(self):
        with self.assertRaises(oracledb.DatabaseError):
            select_ai.delete_credential("nonexistent_cred")
    
    
    def test_delete_nonexistent_cred_without_force(self):
        with self.assertRaises(oracledb.DatabaseError):
            select_ai.delete_credential("nonexistent_cred", force=False)
    

    def test_delete_nonexistent_cred_with_force(self):
        # Should not raise error when force=True
        try:
            select_ai.delete_credential("nonexistent_cred", force=True)
        except Exception as e:
            self.fail(f"delete_credential(force=True) raised {e} unexpectedly.")
    

    def test_delete_cred_local_user(self):
        test_username = "TEST_USER1"

        self.create_local_user(test_username)

        # Connect as test user
        test_env.create_connection(user=test_username, password=self.password)
        # Get credential secret
        credential = self.get_cred_param("GENAI_CRED_USER1")

        try:
            select_ai.delete_credential("GENAI_CRED_USER1", force=True)
        except Exception as e:
            self.fail(f"delete_credential() raised {e} unexpectedly.")

        # Disconnect
        select_ai.disconnect()

        # Clean up user
        test_env.create_connection()
        with select_ai.cursor() as admin_cursor:
            admin_cursor.execute(f"DROP USER {test_username} CASCADE")
    

    def test_invalid_cred_name(self):
        with self.assertRaisesRegex(oracledb.DatabaseError,
                                    r"ORA-20010: Invalid credential name"):
            select_ai.delete_credential("invalid!@#", force=True)
    

    def test_delete_cred_not_connected(self):
        select_ai.disconnect()
        with self.assertRaises(select_ai.errors.DatabaseNotConnectedError):
            select_ai.delete_credential("GENAI_CRED", force=True)
  
    
    def test_credential_name_too_long(self):
        long_name = "GENAI_CRED_" + "a" * 120
        with self.assertRaisesRegex(oracledb.DatabaseError,
                                    r"ORA-20008: Credential name length .* exceeds maximum length"):
            select_ai.delete_credential(long_name, force=True)
    
    
    def test_delete_cred_case_sensitive(self):
        # Create credential
        self.create_test_credential("GENAI_CRED")

        # Try deleting with lower case
        try:
            select_ai.delete_credential(credential_name="genai_cred")
        except Exception as e:
            self.fail(f"async_delete_credential raised {e} unexpectedly for lowercase name")
    

    def test_delete_cred_empty_name(self):
        # Empty string → ORA-20010: Missing credential name
        with self.assertRaisesRegex(oracledb.DatabaseError,
            r"ORA-20010: Missing credential name"):
            select_ai.delete_credential(credential_name="", force=True)

        # None → should also end up with ORA-20010
        with self.assertRaisesRegex(oracledb.DatabaseError,
            r"ORA-20010: Missing credential name"):
            select_ai.delete_credential(credential_name=None, force=True)


if __name__ == "__main__":
    test_env.run_test_cases()
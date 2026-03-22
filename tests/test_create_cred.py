import unittest
import select_ai
import test_env
import oracledb
import os
import time


class TestCreateCredential(unittest.TestCase):
    def setUp(self):
        """
        Setup connection parameters.
        """
        self.user = test_env.get_test_user()
        self.password = test_env.get_test_password()
        self.dsn = test_env.get_localhost_connect_string()
        
        # Get Native cred secrets
        self.user_ocid = test_env.get_user_ocid()
        self.tenancy_ocid = test_env.get_tenancy_ocid()
        self.private_key = test_env.get_private_key()
        self.fingerprint = test_env.get_fingerprint()

        # Get basic cred secrets
        self.cred_username = test_env.get_cred_username()
        self.cred_password = test_env.get_cred_password()
    

    def tearDown(self):
        # Disconnect after each test
        select_ai.disconnect()

    
    def get_native_cred_param(self, cred_name=None) -> dict:
        return dict(
            credential_name = cred_name,
            user_ocid       = self.user_ocid,
            tenancy_ocid    = self.tenancy_ocid,
            private_key     = self.private_key,
            fingerprint     = self.fingerprint
        )
    

    def get_cred_param(self, cred_name=None) -> dict:
        return dict(
            credential_name = cred_name,
            username        = self.cred_username,
            password        = self.cred_password
        )

    
    def drop_credential_cursor(self, cursor, cred_name='GENAI_CRED'):
        cursor.callproc(
            "DBMS_CLOUD.DROP_CREDENTIAL",
            keyword_parameters={
                "credential_name": cred_name
            },
        )


    def test_create_cred(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get credential secret
        credential = self.get_cred_param('GENAI_CRED')

        try:
            select_ai.create_credential(credential=credential, replace=False)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    
    def test_create_cred_twice(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get credential secret
        credential = self.get_cred_param('GENAI_CRED')

        # First creation
        try:
            select_ai.create_credential(credential=credential)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Second creation
        with self.assertRaises(oracledb.DatabaseError) as cm:
            select_ai.create_credential(credential=credential)
        
        
        # Verify specific error code/message
        self.assertIn(
            'ORA-20022', 
            str(cm.exception),
            "Expected ORA-20022 error when creating credential without replace"
        )
        
        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    
    def test_create_cred_same_data_multiple_times(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get credential secret
        credential = self.get_cred_param('GENAI_CRED')

        for _ in range(5):
            select_ai.create_credential(credential=credential, replace=True)
        
        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)
    

    def test_create_cred_rtrue(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get credential secret
        credential = self.get_cred_param('GENAI_CRED')

        try:
            select_ai.create_credential(credential=credential, replace=True)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    
    def test_create_cred_twice_rtrue(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get credential secret
        credential = self.get_cred_param('GENAI_CRED')

        # First creation
        try:
            select_ai.create_credential(credential=credential, replace=True)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Second creation
        try:
            select_ai.create_credential(credential=credential, replace=True)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Assert passed if no exception raised
        self.assertTrue(True, "Credential creation and replacement passed without exception.")
        
        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    
    def test_create_cred_twice_rtrue_rfalse(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get credential secret
        credential = self.get_cred_param('GENAI_CRED')

        # First creation
        try:
            select_ai.create_credential(credential=credential, replace=True)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Second creation
        with self.assertRaises(oracledb.DatabaseError) as cm:
            select_ai.create_credential(credential=credential)
        
        
        # Verify specific error code/message
        self.assertIn(
            'ORA-20022', 
            str(cm.exception),
            "Expected ORA-20022 error when creating credential without replace"
        )
        
        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    
    def test_create_cred_twice_rfalse_rtrue(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get credential secret
        credential = self.get_cred_param('GENAI_CRED')

        # First creation
        try:
            select_ai.create_credential(credential=credential)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Second creation
        try:
            select_ai.create_credential(credential=credential, replace=True)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Assert passed if no exception raised
        self.assertTrue(True, "Credential creation and replacement passed without exception.")
        
        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)


    def test_create_native_cred(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get native cred secrets
        credential = self.get_native_cred_param('GENAI_CRED')

        try:
            select_ai.create_credential(credential=credential, replace=False)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)
    

    def test_create_native_cred_twice(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get native cred secrets
        credential = self.get_native_cred_param('GENAI_CRED')

        # First creation
        try:
            select_ai.create_credential(credential=credential)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Second creation
        with self.assertRaises(oracledb.DatabaseError) as cm:
            select_ai.create_credential(credential=credential)
        
        # Verify specific error code/message
        self.assertIn(
            'ORA-20022', 
            str(cm.exception),
            "Expected ORA-20022 error when creating credential without replace"
        )
        
        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)
    

    def test_create_native_cred_rtrue(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get native cred secrets
        credential = self.get_native_cred_param('GENAI_CRED')

        # First creation
        try:
            select_ai.create_credential(credential=credential, replace=True)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Second creation
        try:
            select_ai.create_credential(credential=credential, replace=True)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Assert passed if no exception raised
        self.assertTrue(True, "Credential creation and replacement passed without exception.")
        
        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    
    def test_create_native_cred_twice_rtrue(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get native cred secrets
        credential = self.get_native_cred_param('GENAI_CRED')

        # Create credential
        try:
            select_ai.create_credential(credential=credential, replace=True)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)

    
    def test_create_cred_empty_name(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get credential secret
        credential = self.get_cred_param()

        # Verify create credential
        with self.assertRaises(Exception) as cm:
            select_ai.create_credential(credential=credential)
        self.assertIn("ORA-20010: Missing credential name", str(cm.exception))

    
    def test_create_cred_empty_dict(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get credential secret
        credential = dict()

        # Verify create credential
        with self.assertRaises(oracledb.DatabaseError) as cm:
            select_ai.create_credential(credential=credential)

        self.assertIn(
            "PLS-00306: wrong number or types of arguments in call to 'CREATE_CREDENTIAL'",
            str(cm.exception)
        )
    

    def test_create_cred_invalid_username(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")
        
        # Get credential secret
        credential = dict(
            credential_name = 'GENAI_CRED',
            username        = 'invalid_username',
            password        = self.cred_password
        )

        try:
            select_ai.create_credential(credential=credential, replace=True)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")

        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)


    def test_create_cred_invalid_password(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")
        
        # Get credential secret
        credential = dict(
            credential_name = 'GENAI_CRED',
            username        = self.cred_username,
            password        = 'invalid_pwd'
        )

        try:
            select_ai.create_credential(credential=credential, replace=True)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")

        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor)
    
    
    def test_create_cred_db_unavailable(self):
        # Get credential secret
        credential = self.get_cred_param('GENAI_CRED')

        with self.assertRaisesRegex(oracledb.InterfaceError,
            r"DPY-1001: not connected to database"):
            select_ai.create_credential(credential=credential, replace=False)


    def test_create_cred_local_user(self):
        test_env.create_connection()

        test_username = "TEST_USER1"
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
        
        # Connect as test user
        test_env.create_connection(user=test_username, password=test_password)
        # Get credential secret
        credential = self.get_cred_param('GENAI_CRED_USER1')

        try:
            select_ai.create_credential(credential=credential, replace=False)
        except Exception as e:
            self.fail(f"create_credential() raised {e} unexpectedly.")
        
        # Drop Credential
        with select_ai.cursor() as cursor:
            self.drop_credential_cursor(cursor, 'GENAI_CRED_USER1')
        
        # Disconnect
        select_ai.disconnect()
    
        # Clean up user
        test_env.create_connection()
        with select_ai.cursor() as admin_cursor:
            admin_cursor.execute(f"DROP USER {test_username} CASCADE")


    # Negative Tests
    def test_create_cred_special_characters(self):
        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get credential secret
        credential = self.get_cred_param('GENAI_CRED!@#')

        with self.assertRaisesRegex(oracledb.DatabaseError, r"ORA-20010: Invalid credential name"):
            select_ai.create_credential(credential=credential, replace=False)
    

    def test_create_cred_long_name(self):
        long_name = "GENAI_CRED" + "_" + "a" * (128 - len('GENAI_CRED'))

        test_env.create_connection()
        self.assertTrue(select_ai.is_connected(), "Connection to DB failed")

        # Get credential secret
        credential = self.get_cred_param(long_name)
        
        with self.assertRaisesRegex(
            oracledb.DatabaseError,
            r"ORA-20008: Credential name length \(129\) exceeds maximum length \(128\)"
        ):
            select_ai.create_credential(credential=credential, replace=False)



if __name__ == "__main__":
    test_env.run_test_cases()

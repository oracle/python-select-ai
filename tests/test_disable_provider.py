import unittest
import select_ai
import test_env
import oracledb
import os
import time


class TestDisableProvider(unittest.TestCase):
    @classmethod
    def create_local_user(cls, test_username="TEST_USER1"):
        """
        Helper to drop and create a local test user with required grants.
        """
        test_password = cls.password

        # Drop user if exists and create new one
        with select_ai.cursor() as admin_cursor:
            try:
                admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            except oracledb.DatabaseError:
                pass  # Ignore if user doesn't exist

            admin_cursor.execute(f"CREATE USER {test_username} IDENTIFIED BY {test_password}")
            admin_cursor.execute(f"grant create session, create table, unlimited tablespace to {test_username}")
            admin_cursor.execute(f"grant execute on dbms_cloud to {test_username}")


    @classmethod
    def setUpClass(cls):
        """
        Create DB users once before all tests.
        """
        # Create connection
        test_env.create_connection()
        assert select_ai.is_connected(), "Connection to DB failed"

        # Assign password from test_env so create_local_user can use it
        cls.user = test_env.get_test_user()
        cls.password = test_env.get_test_password()
        cls.dsn = test_env.get_localhost_connect_string()
        

        cls.db_users = list()
        # Create multiple DB users (DB_USER1 ... DB_USER5)
        for i in range(1, 6):
            user = f"DB_USER{i}"
            cls.create_local_user(user)
            cls.db_users.append(user)
        
        # Create Additional user
        cls.create_local_user("DB_USER6")
    
    
    @classmethod
    def tearDownClass(cls):
        """
        Drop DB users after all tests finish.
        """
        cls.db_users.append("DB_USER6")
        with select_ai.cursor() as admin_cursor:
            for user in cls.db_users:
                try:
                    admin_cursor.execute(f"DROP USER {user} CASCADE")
                except oracledb.DatabaseError:
                    pass  # Ignore if already dropped

        # Disconnect from DB
        try:
            select_ai.disconnect()
        except Exception as e:
            print(f"Warning: disconnect failed ({e})")
    
    
    def setUp(self):
        self.provider_endpoint = "*.openai.azure.com"
        self.db_users = self.__class__.db_users

        # Enabling provider with valid users
        try:
            select_ai.enable_provider(
                users=self.db_users,
                provider_endpoint=self.provider_endpoint
            )
        except Exception as e:
            self.fail(f"enable_provider() raised {e} unexpectedly.")


    def test_disable_provider_success(self):
        # Disabling provider for valid users and endpoint should succeed.
        try:
            select_ai.disable_provider(
                users=self.db_users,
                provider_endpoint=self.provider_endpoint
            )
        except Exception as e:
            self.fail(f"disable_provider() raised {e} unexpectedly.")
    

    def test_disable_provider_nonexistent_user(self):
        # Disabling provider with non-existent users should raise DatabaseError.
        db_users = ["DB_USER1", "TEST_USER2"]

        with self.assertRaises(oracledb.DatabaseError):
            select_ai.disable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )


    def test_disable_provider_nonexistent_users(self):
        # Disabling provider with non-existent users should raise DatabaseError.
        with self.assertRaises(oracledb.DatabaseError):
            select_ai.disable_provider(
                users=["INVALID_USER1", "INVALID_USER2"],
                provider_endpoint=self.provider_endpoint
            )
    
    
    def test_disable_provider_invalid_users_type_int(self):
        # Disabling provider with int as users should raise TypeError/ValueError.
        with self.assertRaises((TypeError, ValueError)):
            select_ai.disable_provider(
                users=123,
                provider_endpoint=self.provider_endpoint
            )
    
    
    def test_disable_provider_invalid_users_type_string(self):
        # Disabling provider with string instead of list should raise TypeError/ValueError.
        with self.assertRaises((TypeError, ValueError)):
            select_ai.disable_provider(
                users="DB_USER1",
                provider_endpoint=self.provider_endpoint
            )


    def test_disable_provider_invalid_users_type_none(self):
        # Disabling provider with None as users should raise TypeError/ValueError.
        with self.assertRaises((TypeError, ValueError)):
            select_ai.disable_provider(
                users=None,
                provider_endpoint=self.provider_endpoint
            )
    
    
    def test_disable_provider_missing_endpoint(self):
        # None endpoint should raise ValueError.
        with self.assertRaises(ValueError):
            select_ai.disable_provider(
                users=self.db_users,
                provider_endpoint=None
            )
    
    
    def test_disable_provider_invalid_endpoint(self):
        # Disabling provider with invalid endpoint should raise DatabaseError.
        with self.assertRaises(oracledb.DatabaseError):
            select_ai.disable_provider(
                users=self.db_users,
                provider_endpoint="invalid.endpoint"
            )
    
    
    def test_disable_provider_with_empty_users(self):
        # Disabling provider with empty users list should succeed without error.
        try:
            select_ai.disable_provider(
                users=[],
                provider_endpoint=self.provider_endpoint
            )
        except Exception as e:
            self.fail(f"disable_provider() raised {e} unexpectedly with empty users list.")
    

    def test_disable_provider_duplicate_users(self):
        # Disabling provider with duplicate users should raise ORA-01927
        with self.assertRaises(oracledb.DatabaseError) as cm:
            select_ai.disable_provider(
                users=[self.db_users[0], self.db_users[0]],
                provider_endpoint=self.provider_endpoint
            )

        # Verify error code is ORA-01927
        self.assertIn("ORA-01927", str(cm.exception))
    

    def test_disable_provider_case_insensitive_username(self):
        # Lowercase username should work if DB is case-insensitive
        try:
            select_ai.disable_provider(
                users=[self.db_users[0].lower()],
                provider_endpoint=self.provider_endpoint
            )
        except Exception as e:
            self.fail(f"disable_provider() raised {e} unexpectedly with lowercase username.")

    
    def test_disable_provider_username_with_whitespace(self):
        # Leading/trailing whitespace should be ignored and still succeed
        db_users = [f"  {self.db_users[0]}  "]
        try:
            select_ai.disable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )
        except Exception as e:
            self.fail(f"disable_provider() raised {e} unexpectedly with whitespace in username.")
    
    
    def test_disable_provider_valid_custom_endpoint(self):
        # Enabling provider with a custom endpoint should raise ORA-24244
        with self.assertRaisesRegex(
            oracledb.DatabaseError,
            r"ORA-24244: invalid host or port for access control list \(ACL\) assignment"
        ):
            select_ai.disable_provider(
                users=self.db_users,
                provider_endpoint="https://custom.openai.azure.com"
            )
    
    
    def test_disable_provider_non_granted_user(self):
        # Disabling provider for a user who was never granted access should raise DatabaseError.
        non_granted_user = "DB_USER6"

        with self.assertRaises(oracledb.DatabaseError) as cm:
            select_ai.disable_provider(
                users=[non_granted_user],
                provider_endpoint=self.provider_endpoint
            )

        # Optionally check the specific Oracle error code
        self.assertIn("ORA-01927", str(cm.exception))



    def test_disable_provider_large_user_list(self):
        db_users = [f"DB_USER_{i}" for i in range(1000)]
        with self.assertRaises(oracledb.DatabaseError):
            select_ai.disable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )


if __name__ == "__main__":
    test_env.run_test_cases()
import unittest
import select_ai
import test_env
import oracledb
import os
import time



class TestEnableProvider(unittest.TestCase):
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
    
    
    @classmethod
    def tearDownClass(cls):
        """
        Drop DB users after all tests finish.
        """
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


    def test_enable_provider_success(self):
        # Enabling provider with valid users and endpoint should succeed.
        try:
            select_ai.enable_provider(
                users=self.db_users,
                provider_endpoint=self.provider_endpoint
            )
        except Exception as e:
            self.fail(f"enable_provider() raised {e} unexpectedly.")
    
    
    def test_enable_provider_nonexistent_username(self):
        # Enabling provider with nonexistent users should raise DatabaseError
        db_users = ["DB_USER1", "TEST_USER2"]

        with self.assertRaisesRegex(
            oracledb.DatabaseError,
            r"ORA-01917: user or role 'TEST_USER2' does not exist"
        ):
            select_ai.enable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )


    def test_enable_provider_nonexistent_usernames(self):
        # Enabling provider with nonexistent users should raise DatabaseError
        db_users = ["TEST_USER1", "TEST_USER2"]

        with self.assertRaisesRegex(
            oracledb.DatabaseError,
            r"ORA-01917: user or role 'TEST_USER1' does not exist"
        ):
            select_ai.enable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )


    def test_enable_provider_empty_users(self):
        # Empty users list should raise ValueError.
        try:
            select_ai.enable_provider(
                users=[],
                provider_endpoint=self.provider_endpoint
            )
        except Exception as e:
            self.fail(f"enable_provider() raised {e} unexpectedly with empty users.")


    def test_enable_provider_invalid_users_type(self):
        # Passing users as non-list should raise TypeError.
        with self.assertRaises(TypeError):
            select_ai.enable_provider(
                users="DB_USER1",   # not a list
                provider_endpoint=self.provider_endpoint
            )
  

    def test_enable_provider_invalid_users_type_int(self):
        # Passing users as non-list should raise TypeError.
        with self.assertRaises(TypeError):
            select_ai.enable_provider(
                users=2,   # not a list
                provider_endpoint=self.provider_endpoint
            )


    def test_enable_provider_missing_endpoint(self):
        # None endpoint should raise ValueError.
        with self.assertRaises(ValueError):
            select_ai.enable_provider(
                users=self.db_users,
                provider_endpoint=None
            )


    def test_enable_provider_invalid_endpoint(self):
        # DatabaseError from underlying call should propagate.
        with self.assertRaises(ValueError):
            select_ai.enable_provider(
                users=self.db_users,
                provider_endpoint="invalid.endpoint"
            )
    

    def test_enable_provider_duplicate_users(self):
        # Duplicate users should not cause failure
        try:
            select_ai.enable_provider(
                users=[self.db_users[0], self.db_users[0]],
                provider_endpoint=self.provider_endpoint
            )
        except Exception as e:
            self.fail(f"enable_provider() raised {e} unexpectedly with duplicate users.")
    

    def test_enable_provider_case_insensitive_username(self):
        # Lowercase username should work if DB is case-insensitive
        try:
            select_ai.enable_provider(
                users=[self.db_users[0].lower()],
                provider_endpoint=self.provider_endpoint
            )
        except Exception as e:
            self.fail(f"enable_provider() raised {e} unexpectedly with lowercase username.")
    

    def test_enable_provider_username_with_whitespace(self):
        # Leading/trailing whitespace should be ignored and still succeed
        db_users = [f"  {self.db_users[0]}  "]
        try:
            select_ai.enable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )
        except Exception as e:
            self.fail(f"enable_provider() raised {e} unexpectedly with whitespace in username.")
    

    def test_enable_provider_large_user_list(self):
        db_users = [f"DB_USER_{i}" for i in range(1000)]
        with self.assertRaises(oracledb.DatabaseError):
            select_ai.enable_provider(
                users=db_users,
                provider_endpoint=self.provider_endpoint
            )


    def test_enable_provider_valid_custom_endpoint(self):
        # Enabling provider with a custom endpoint should raise ORA-24244
        with self.assertRaisesRegex(
            oracledb.DatabaseError,
            r"ORA-24244: invalid host or port for access control list \(ACL\) assignment"
        ):
            select_ai.enable_provider(
                users=self.db_users,
                provider_endpoint="https://custom.openai.azure.com"
            )


if __name__ == "__main__":
    test_env.run_test_cases()
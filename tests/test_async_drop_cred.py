import unittest
import select_ai
import test_env
import oracledb
import os
import asyncio


class TestAsyncDropCredential(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """
        Async setup for test connection parameters and connection creation.
        """
        self.user = test_env.get_test_user()
        self.password = test_env.get_test_password()
        self.dsn = test_env.get_localhost_connect_string()

        # Get basic cred secrets
        self.cred_username = test_env.get_cred_username()
        self.cred_password = test_env.get_cred_password()

        # Create async connection
        await test_env.create_async_connection(
            dsn=self.dsn, use_wallet=False
        )

        is_connected = await select_ai.async_is_connected()
        self.assertTrue(is_connected, "Connection to DB failed")

    
    async def asyncTearDown(self):
        # Disconnect after each test
        await select_ai.async_disconnect()
    

    def get_cred_param(self, cred_name=None) -> dict:
        return dict(
            credential_name = cred_name,
            username        = self.cred_username,
            password        = self.cred_password
        )

    async def create_test_credential(self, cred_name="GENAI_CRED"):
        """
        Async helper to create a test credential.
        """
        # Get credential secret
        credential = self.get_cred_param(cred_name)

        try:
            await select_ai.async_create_credential(
                credential=credential,
                replace=False
            )
        except Exception as e:
            self.fail(f"async_create_credential() raised {e} unexpectedly.")
    

    async def create_local_user(self, test_username="TEST_USER1"):
        """
        Async helper to drop and create a local test user with required grants.
        """
        test_password = self.password

        # Drop user if exists and create new one
        async with select_ai.async_cursor() as admin_cursor:
            try:
                await admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            except oracledb.DatabaseError:
                pass  # Ignore if user doesn't exist

            await admin_cursor.execute(f"CREATE USER {test_username} IDENTIFIED BY {test_password}")
            await admin_cursor.execute(f"grant create session, create table, unlimited tablespace to {test_username}")
            await admin_cursor.execute(f"grant execute on dbms_cloud to {test_username}")


    async def test_async_delete_cred_success(self):
        # Create credential
        await self.create_test_credential()

        try:
            await select_ai.async_delete_credential("GENAI_CRED", force=True)
        except Exception as e:
            self.fail(f"delete_credential() raised {e} unexpectedly.")
    
    
    async def test_async_delete_cred_twice_force_true(self):
        # Create credential
        await self.create_test_credential()

        # First delete should succeed
        await select_ai.async_delete_credential("GENAI_CRED", force=True)

        # Second delete should also succeed (no exception, since force=True)
        await select_ai.async_delete_credential("GENAI_CRED", force=True)

    
    async def test_async_delete_cred_twice_force_false(self):
        # Create credential
        await self.create_test_credential()

        # First delete should succeed
        await select_ai.async_delete_credential("GENAI_CRED", force=False)

        # Second delete should raise DatabaseError since credential is already deleted
        with self.assertRaises(oracledb.DatabaseError):
            await select_ai.async_delete_credential("GENAI_CRED", force=False)
    

    async def test_async_delete_nonexistent_cred_default(self):
        with self.assertRaises(oracledb.DatabaseError):
            await select_ai.async_delete_credential("nonexistent_cred")
    
    
    async def test_async_delete_nonexistent_cred_without_force(self):
        with self.assertRaises(oracledb.DatabaseError):
            await select_ai.async_delete_credential("nonexistent_cred", force=False)
    

    async def test_async_delete_nonexistent_cred_with_force(self):
        # Should not raise error when force=True
        try:
            await select_ai.async_delete_credential("nonexistent_cred", force=True)
        except Exception as e:
            self.fail(f"delete_credential(force=True) raised {e} unexpectedly.")
    

    async def test_async_delete_cred_local_user(self):
        test_username = "TEST_USER1"

        await self.create_local_user(test_username)

        # Connect as test user
        await test_env.create_async_connection(
            user=test_username,
            password=self.password,
            dsn=self.dsn,
            use_wallet=False
        )

        # Get credential secret
        credential = self.get_cred_param("GENAI_CRED_USER1")

        try:
            await select_ai.async_delete_credential("GENAI_CRED_USER1", force=True)
        except Exception as e:
            self.fail(f"delete_credential() raised {e} unexpectedly.")

        # Disconnect
        await select_ai.async_disconnect()

        # Clean up user
        await test_env.create_async_connection(
            dsn=self.dsn, use_wallet=False
        )
        async with select_ai.async_cursor() as admin_cursor:
            await admin_cursor.execute(f"DROP USER {test_username} CASCADE")
    

    async def test_async_invalid_cred_name(self):
        with self.assertRaisesRegex(oracledb.DatabaseError,
                                    r"ORA-20010: Invalid credential name"):
            await select_ai.async_delete_credential("invalid!@#", force=True)
    

    async def test_async_delete_cred_not_connected(self):
        await select_ai.async_disconnect()
        with self.assertRaises(select_ai.errors.DatabaseNotConnectedError):
            await select_ai.async_delete_credential("GENAI_CRED", force=True)
  
    
    async def test_async_credential_name_too_long(self):
        long_name = "GENAI_CRED_" + "a" * 120
        with self.assertRaisesRegex(oracledb.DatabaseError,
                                    r"ORA-20008: Credential name length .* exceeds maximum length"):
            await select_ai.async_delete_credential(long_name, force=True)
    
    
    async def test_async_delete_cred_case_sensitive(self):
        # Create credential
        await self.create_test_credential("GENAI_CRED")

        # Try deleting with lower case
        try:
            await select_ai.async_delete_credential(credential_name="genai_cred")
        except Exception as e:
            self.fail(f"async_delete_credential raised {e} unexpectedly for lowercase name")
    

    async def test_async_delete_cred_empty_name(self):
        # Empty string → ORA-20010: Missing credential name
        with self.assertRaisesRegex(oracledb.DatabaseError,
            r"ORA-20010: Missing credential name"):
            await select_ai.async_delete_credential(credential_name="", force=True)

        # None → should also end up with ORA-20010
        with self.assertRaisesRegex(oracledb.DatabaseError,
            r"ORA-20010: Missing credential name"):
            await select_ai.async_delete_credential(credential_name=None, force=True)


if __name__ == "__main__":
    test_env.run_test_cases()
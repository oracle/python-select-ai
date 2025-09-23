import unittest
import select_ai
import test_env
import oracledb
import os
import asyncio


class TestAsyncEnableProvider(unittest.IsolatedAsyncioTestCase):
    @classmethod
    async def create_async_local_user(cls, test_username="TEST_USER1"):
        """
        Helper to drop and create a local test user with required grants.
        """
        test_password = cls.password

        # Drop user if exists and create new one
        async with select_ai.async_cursor() as admin_cursor:
            try:
                await admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            except oracledb.DatabaseError:
                pass  # Ignore if user doesn't exist

            await admin_cursor.execute(f"CREATE USER {test_username} IDENTIFIED BY {test_password}")
            await admin_cursor.execute(f"grant create session, create table, unlimited tablespace to {test_username}")
            await admin_cursor.execute(f"grant execute on dbms_cloud to {test_username}")


    @classmethod
    async def _asyncSetUpClass(cls):
        """
        Create DB users once before all tests.
        """
        # Assign password from test_env so create_local_user can use it
        cls.user = test_env.get_test_user()
        cls.password = test_env.get_test_password()
        cls.dsn = test_env.get_localhost_connect_string()

        # Create async connection
        await test_env.create_async_connection(
            dsn=cls.dsn, use_wallet=False
        )
        is_connected = await select_ai.async_is_connected()
        assert is_connected, "Connection to DB failed"
        

        cls.db_users = list()
        # Create multiple DB users (DB_USER1 ... DB_USER5)
        for i in range(1, 6):
            user = f"DB_USER{i}"
            await cls.create_async_local_user(user)
            cls.db_users.append(user)
      
    @classmethod
    def setUpClass(cls):
        """
        Sync wrapper that runs async setup once for all tests.
        """
        asyncio.run(cls._asyncSetUpClass())


    @classmethod
    async def _asyncTearDownClass(cls):
        """
        Drop DB users after all tests finish.
        """
        async with select_ai.async_cursor() as admin_cursor:
            for user in cls.db_users:
                try:
                    await admin_cursor.execute(f"DROP USER {user} CASCADE")
                except oracledb.DatabaseError:
                    pass  # Ignore if already dropped

        # Disconnect from DB
        try:
            await select_ai.async_disconnect()
        except Exception as e:
            print(f"Warning: disconnect failed ({e})")

    
    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls._asyncTearDownClass())


    async def asyncSetUp(self):
        self.provider_endpoint = "*.openai.azure.com"


    async def test_async_enable_provider_success(self):
        # Enabling provider with valid users and endpoint should succeed.
        try:
            await select_ai.async_enable_provider(
                users=self.__class__.db_users,
                provider_endpoint=self.provider_endpoint
            )
        except Exception as e:
            self.fail(f"enable_provider() raised {e} unexpectedly.")


if __name__ == "__main__":
    test_env.run_test_cases()
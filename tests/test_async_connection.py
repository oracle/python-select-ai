import unittest
import select_ai
import test_env
import oracledb
import os
import asyncio


class TestCase(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        """
        Setup connection parameters.
        """
        self.user = test_env.get_test_user()
        self.password = test_env.get_test_password()
        self.dsn = test_env.get_localhost_connect_string()

    # --- Connection Tests ---
    # async def test_async_connection_success(self):
    #     try:
    #         # Use the helper function to create the connection
    #         await test_env.create_async_connection(use_wallet=True)

    #         # Check if connected
    #         is_connected = await select_ai.async_is_connected()
    #         self.assertTrue(is_connected, "Connection to DB failed")

    #     finally:
    #         if is_connected:
    #             await select_ai.async_disconnect()
    #             # Ensure connection is now closed
    #             is_still_connected = await select_ai.async_is_connected()
    #             self.assertFalse(is_still_connected, "Connection should be closed after close()")


    async def test_async_connection_without_wallet(self):
        try:
            # Use helper to create async connection without wallet
            await test_env.create_async_connection(
                dsn=self.dsn, use_wallet=False
            )

            # Check if connected
            is_connected = await select_ai.async_is_connected()
            self.assertTrue(is_connected, "Connection to DB failed without wallet")
        finally:
            if is_connected:
                await select_ai.async_disconnect()
                # Ensure connection is now closed
                is_still_connected = await select_ai.async_is_connected()
                self.assertFalse(is_still_connected, "Connection should be closed after close()")
    

    async def test_async_is_connected_bool(self):
        # connection version is a string
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)
        is_connected = await select_ai.async_is_connected()
        self.assertIsInstance(is_connected, bool)
        await select_ai.async_disconnect()

    async def test_async_conn_failure_wrong_password(self):
        with self.assertRaises(oracledb.DatabaseError):
            await select_ai.async_connect(user=self.user, password="wrong_pass", dsn=self.dsn)
    

    async def test_async_connect_bad_string(self):
        # connection to database with bad connect string
        with self.assertRaises(TypeError) as cm:
            await select_ai.async_connect("not a valid connect string!!")

        self.assertIn(
            "missing 2 required positional arguments",
            str(cm.exception)
        )


    async def test_async_connect_bad_dsn(self):
        # Expecting a standard DatabaseError for bad DSN
        dsn = 'invalid_dsn'
        with self.assertRaises(oracledb.DatabaseError) as context:
            await select_ai.async_connect(user=self.user, password=self.password, dsn=dsn)
        
        self.assertIn("DPY-4027", str(context.exception))
    

    async def test_asyn_connect_bad_password(self):
        # connection to database with bad password
        with self.assertRaises(oracledb.DatabaseError) as cm:
            await select_ai.async_connect(user=self.user, password=test_env.get_test_password() + "X", dsn=self.dsn)
        
        # Validate that the error contains ORA-01017
        self.assertIn("ORA-01017", str(cm.exception))
    

    # --- Query Tests ---
    async def test_async_query_execution(self):
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)
        async with select_ai.async_cursor() as cr:
            await cr.execute("SELECT 1 FROM DUAL")
            result = await cr.fetchone()
            self.assertEqual(result[0], 1)

        # Disconnect
        await select_ai.async_disconnect()


    async def test_async_query_with_parameters(self):
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)
        async with select_ai.async_cursor() as cr:
            await cr.execute("SELECT :val FROM dual", val=42)
            result = await cr.fetchone()
            self.assertEqual(result[0], 42)

        # Disconnect
        await select_ai.async_disconnect()
    

    async def test_async_fetchall(self):
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)
        async with select_ai.async_cursor() as cursor:
            await cursor.execute("SELECT level FROM dual CONNECT BY level <= 5")
            results = await cursor.fetchall()
            self.assertEqual(len(results), 5)
        
        # Disconnect
        await select_ai.async_disconnect()


    async def test_async_invalid_query(self):
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)
        async with select_ai.async_cursor() as cursor:
            with self.assertRaises(oracledb.DatabaseError):
                await cursor.execute("SELECT * FROM non_existent_table")
        
        # Disconnect
        await select_ai.async_disconnect()
    

    # --- Transaction Tests ---
    async def test_async_commit_and_rollback(self):
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)
        async with select_ai.async_cursor() as cursor:
            # Create the table only if it doesn't exist
            await cursor.execute("""
                begin
                    execute immediate 'create table test_cr_tab (id int)';
                exception
                    when others then
                        if sqlcode != -955 then
                            raise;
                        end if;
                end;
            """)
            await cursor.execute("commit")

            # Clean up any leftover data
            await cursor.execute("truncate table test_cr_tab")

            # Test rollback
            await cursor.execute("insert into test_cr_tab values (1)")
            await cursor.execute("rollback")

            await cursor.execute("select count(*) from test_cr_tab")
            (count,) = await cursor.fetchone()
            print (count)
            self.assertEqual(count, 0, "Rollback should undo the insert.")
        
        # Disconnect
        await select_ai.async_disconnect()
    

    # --- Lifecycle Tests ---
    async def test_async_connection_close(self):
        # Create connection
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)

        # Close connection
        await select_ai.async_disconnect()

        # Attempt to use cursor after disconnect should raise InterfaceError
        with self.assertRaises(oracledb.InterfaceError):
            async with select_ai.async_cursor() as cr:
                await cr.execute("SELECT 1 FROM DUAL")
    

    async def test_async_connection_reclose(self):
        # Create connection
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)

        # First disconnect
        await select_ai.async_disconnect()
        # Second disconnect should not raise
        await select_ai.async_disconnect()

        # Assert connection is closed
        is_connected = await select_ai.async_is_connected()
        self.assertFalse(is_connected, "Connection should be closed after repeated disconnects")


    async def test_async_dbms_output(self):
        # Create connection
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)

        test_string = "Testing DBMS_OUTPUT package"

        async with select_ai.async_cursor() as cursor:
            await cursor.callproc("dbms_output.enable")
            await cursor.callproc("dbms_output.put_line", [test_string])
            string_var = cursor.var(str)
            number_var = cursor.var(int)
            await cursor.callproc("dbms_output.get_line", (string_var, number_var))
            self.assertEqual(string_var.getvalue(), test_string)

        # Disconnect
        await select_ai.async_disconnect()


    async def test_async_connection_instance(self):
        # Create connection
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)

        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                """
                select upper(sys_context('userenv', 'instance_name'))
                from dual
                """
            )
            (instance_name,) = await cursor.fetchone()
            self.assertIsInstance(instance_name, str, "Expected service_name to be a string")
    
        # Disconnect
        await select_ai.async_disconnect()

    async def test_async_max_open_cursors(self):
        # test getting max_open_cursors
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)

        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                "select value from V$PARAMETER where name='open_cursors'"
            )
            (max_open_cursors,) = await cursor.fetchone()

        self.assertEqual(1000, int(max_open_cursors))

        # Disconnect
        await select_ai.async_disconnect()


    async def test_async_get_service_name(self):
        # test getting service_name
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)

        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                "select sys_context('userenv', 'service_name') from dual"
            )
            (service_name,) = await cursor.fetchone()
        
        # Verify service_name is a string
        self.assertIsInstance(service_name, str, "Expected service_name to be a string")

        # Disconnect
        await select_ai.async_disconnect()


    async def test_async_create_user_and_table(self):
        # Create connection
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)

        test_username = "TEST_USER1"
        test_password = self.password

        # Drop user if exists and create new one
        async with select_ai.async_cursor() as admin_cursor:
            try:
                await admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            except oracledb.DatabaseError:
                pass  # Ignore if user doesn't exist

            await admin_cursor.execute(f"CREATE USER {test_username} IDENTIFIED BY {test_password}")
            await admin_cursor.execute(f"grant create session, create table, unlimited tablespace to {test_username}")
            await admin_cursor.execute("commit")

        # Connect as test user
        await test_env.create_async_connection(user=test_username, password=test_password, dsn=self.dsn, use_wallet=False)

        async with select_ai.async_cursor() as test_cursor:
            await test_cursor.execute("CREATE TABLE test_table (id INT)")
            await test_cursor.execute("INSERT INTO test_table (id) VALUES (100)")
            await test_cursor.execute("commit")

            await test_cursor.execute("SELECT id FROM test_table")
            result = await test_cursor.fetchone()
            self.assertEqual(result[0], 100)
        
        # Disconnect
        await select_ai.async_disconnect()

        # Clean up user
        await test_env.create_async_connection(dsn=self.dsn, use_wallet=False)
        async with select_ai.async_cursor() as admin_cursor:
            await admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            await admin_cursor.execute("commit")

        # Disconnect
        await select_ai.async_disconnect()


if __name__ == "__main__":
    test_env.run_test_cases()
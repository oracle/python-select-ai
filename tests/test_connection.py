import unittest
import select_ai
import test_env
import oracledb
import os
import time


class TestCase(unittest.TestCase):

    def setUp(self):
        """
        Setup connection parameters.
        """
        self.user = test_env.get_test_user()
        self.password = test_env.get_test_password()
        self.dsn = test_env.get_localhost_connect_string()

        test_env.create_connection()
        with select_ai.cursor() as cursor:
            cursor.execute("""
                begin
                    execute immediate 'create table testtemptable (intcol int)';
                exception
                    when others then
                        if sqlcode != -955 then
                            raise;
                        end if;
                end;
            """)
            cursor.execute("commit")


    # --- Connection Tests ---
    def test_connection_success(self):
        try:
            # Use the helper function to create the connection
            test_env.create_connection(use_wallet=True)
            is_connected = select_ai.is_connected()
            self.assertTrue(is_connected, "Connection to DB failed")
        finally:
            if is_connected:
                select_ai.disconnect()
                self.assertFalse(select_ai.is_connected(), "Connection to DB failed")
    
    
    def test_connection_without_wallet(self):
        try:
            # Use the helper function to create the connection
            test_env.create_connection(dsn=self.dsn, use_wallet=False)
            is_connected = select_ai.is_connected()
            self.assertTrue(is_connected, "Connection to DB failed")
        finally:
            if is_connected:
                select_ai.disconnect()
                self.assertFalse(select_ai.is_connected(), "Connection to DB failed")
    

    def test_is_connected_bool(self):
        # connection version is a string
        test_env.create_connection()
        self.assertIsInstance(select_ai.is_connected(), bool)
        select_ai.disconnect()


    def test_conn_failure_wrong_password(self):
        with self.assertRaises(oracledb.DatabaseError):
            select_ai.connect(user=self.user, password="wrong_pass", dsn=self.dsn)


    def test_connect_bad_string(self):
        # connection to database with bad connect string
        with self.assertRaises(TypeError) as cm:
            select_ai.connect("not a valid connect string!!")

        self.assertIn(
            "missing 2 required positional arguments",
            str(cm.exception)
        )


    def test_connect_bad_dsn(self):
        # Expecting a standard DatabaseError for bad DSN
        dsn = 'invalid_dsn'
        with self.assertRaises(oracledb.DatabaseError) as context:
            select_ai.connect(user=self.user, password=self.password, dsn=dsn)
        
        self.assertIn("DPY-4027", str(context.exception))


    def test_connect_bad_password(self):
        # connection to database with bad password
        with self.assertRaises(oracledb.DatabaseError) as cm:
            select_ai.connect(user=self.user, password=test_env.get_test_password() + "X", dsn=self.dsn)
        
        # Validate that the error contains ORA-01017
        self.assertIn("ORA-01017", str(cm.exception))


    # --- Query Tests ---
    def test_query_execution(self):
        test_env.create_connection()
        with select_ai.cursor() as cr:
            cr.execute("SELECT 1 FROM DUAL")
            result = cr.fetchone()
            self.assertEqual(result[0], 1)

        # Disconnect
        select_ai.disconnect()

    def test_query_with_parameters(self):
        test_env.create_connection()
        with select_ai.cursor() as cr:
            cr.execute("SELECT :val FROM dual", val=42)
            result = cr.fetchone()
            self.assertEqual(result[0], 42)
        
        # Disconnect
        select_ai.disconnect()

    def test_fetchall(self):
        test_env.create_connection()
        with select_ai.cursor() as cursor:
            cursor.execute("SELECT level FROM dual CONNECT BY level <= 5")
            results = cursor.fetchall()
            self.assertEqual(len(results), 5)
        
        # Disconnect
        select_ai.disconnect()

    def test_invalid_query(self):
        test_env.create_connection()
        with select_ai.cursor() as cursor:
            with self.assertRaises(oracledb.DatabaseError):
                cursor.execute("SELECT * FROM non_existent_table")
        
        # Disconnect
        select_ai.disconnect()


    # --- Transaction Tests ---
    def test_commit_and_rollback(self):
        test_env.create_connection()
        with select_ai.cursor() as cursor:
            # Create the table only if it doesn't exist
            cursor.execute("""
                begin
                    execute immediate 'create table test_cr_tab (id int)';
                exception
                    when others then
                        if sqlcode != -955 then
                            raise;
                        end if;
                end;
            """)
            cursor.execute("commit")

            # Clean up any leftover data
            cursor.execute("truncate table test_cr_tab")

            # Test rollback
            cursor.execute("insert into test_cr_tab values (1)")
            cursor.execute("rollback")

            cursor.execute("select count(*) from test_cr_tab")
            (count,) = cursor.fetchone()
            self.assertEqual(count, 0, "Rollback should undo the insert.")


    # --- Lifecycle Tests ---
    def test_connection_close(self):
        # Create connection
        test_env.create_connection()

        # Close connection
        select_ai.disconnect()

        # Attempt to use cursor after disconnect should raise InterfaceError
        with self.assertRaises(oracledb.InterfaceError):
            with select_ai.cursor() as cr:
                cr.execute("SELECT 1 FROM DUAL")


    def test_connection_reclose(self):
        # Create connection
        test_env.create_connection()

        # First disconnect
        select_ai.disconnect()
        # Second disconnect should not raise
        select_ai.disconnect()

        # Assert connection is closed
        is_connected = select_ai.is_connected()
        self.assertFalse(is_connected, "Connection should be closed after repeated disconnects")

    
    def test_dbms_output(self):
        # test dbms_output package
        test_env.create_connection()
        test_string = "Testing DBMS_OUTPUT package"

        with select_ai.cursor() as cursor:
            cursor.callproc("dbms_output.enable")
            cursor.callproc("dbms_output.put_line", [test_string])
            string_var = cursor.var(str)
            number_var = cursor.var(int)
            cursor.callproc("dbms_output.get_line", (string_var, number_var))
            self.assertEqual(string_var.getvalue(), test_string)
        
        # Disconnect
        select_ai.disconnect()
    
    
    def test_connection_instance(self):
        # test connection instance name
        test_env.create_connection()

        with select_ai.cursor() as cursor:
            cursor.execute(
                """
                select upper(sys_context('userenv', 'instance_name'))
                from dual
                """
            )
            (instance_name,) = cursor.fetchone()
            self.assertIsInstance(instance_name, str, "Expected service_name to be a string")
    
        # Disconnect
        select_ai.disconnect()


    def test_max_open_cursors(self):
        # test getting max_open_cursors
        test_env.create_connection()

        with select_ai.cursor() as cursor:
            cursor.execute(
                "select value from V$PARAMETER where name='open_cursors'"
            )
            (max_open_cursors,) = cursor.fetchone()
        
        self.assertEqual(1000, int(max_open_cursors))

        # Disconnect
        select_ai.disconnect()


    def test_get_service_name(self):
        # test getting service_name
        test_env.create_connection()

        with select_ai.cursor() as cursor:
            cursor.execute(
                "select sys_context('userenv', 'service_name') from dual"
            )
            (service_name,) = cursor.fetchone()
        
        # Verify service_name is a string
        self.assertIsInstance(service_name, str, "Expected service_name to be a string")

        # Disconnect
        select_ai.disconnect()


    def test_create_user_and_table(self):
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


        # Connect as test user
        test_env.create_connection(user=test_username, password=test_password)

        with select_ai.cursor() as test_cursor:
            test_cursor.execute("CREATE TABLE test_table (id INT)")
            test_cursor.execute("INSERT INTO test_table (id) VALUES (100)")
            # test_user_conn.commit()

            test_cursor.execute("SELECT id FROM test_table")
            result = test_cursor.fetchone()
            self.assertEqual(result[0], 100)
        
        # Disconnect
        select_ai.disconnect()

        # Clean up user
        test_env.create_connection()
        with select_ai.cursor() as admin_cursor:
            admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            # admin_conn.commit()


if __name__ == "__main__":
    # unittest.main()
    test_env.run_test_cases()

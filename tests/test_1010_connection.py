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

logger = logging.getLogger("TestConnection")

@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO
    )

@pytest.fixture(scope="class")
def connection_params(request):
    params = {
        "user":             test_env.get_test_user(),
        "password":         test_env.get_test_password(),
        "dsn":              test_env.get_connect_string(),
        "use_wallet":       test_env.get_use_wallet(),
        "wallet_location":  test_env.get_wallet_location(),
        "wallet_password":  test_env.get_wallet_password(),
        "connect_kwargs":   {},
    }
    request.cls.connection_params = params

@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown(request, connection_params):
    logger.info("=== Setting up TestConnection class ===")
    test_env.create_connection(
        dsn=request.cls.connection_params["dsn"],
        use_wallet=request.cls.connection_params["use_wallet"]
    )
    assert select_ai.is_connected(), "Connection to DB failed"
    logger.info("Initial connection successful")
    yield
    logger.info("=== Tearing down TestConnection class ===")
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

@pytest.mark.usefixtures("connection_params", "setup_and_teardown")
class TestConnection:
    def test_1011(self):
        """Testing connection success with wallet."""
        logger.info("Testing connection success with wallet...")
        test_env.create_connection(use_wallet=True)
        is_connected = select_ai.is_connected()
        assert is_connected, "Connection to DB failed"
        logger.info("Connection successful")
        select_ai.disconnect()
        assert not select_ai.is_connected(), "Connection should be closed after disconnect"
        logger.info("Disconnected after test_01_connection_success")

    def test_1012(self):
        """Testing connection without wallet."""
        logger.info("Testing connection without wallet...")
        test_env.create_connection(use_wallet=False)
        is_connected = select_ai.is_connected()
        assert is_connected, "Connection to DB failed without wallet"
        logger.info("Connection successful without wallet")
        select_ai.disconnect()
        assert not select_ai.is_connected(), "Connection should be closed after close()"
        logger.info("Disconnected after test_02_without_wallet")

    def test_1013(self):
        """Testing is_connected returns bool."""
        logger.info("Testing is_connected returns bool...")
        test_env.create_connection(use_wallet=self.connection_params["use_wallet"])
        assert isinstance(select_ai.is_connected(), bool)
        select_ai.disconnect()
        logger.info("is_connected check complete and disconnected")

    def test_1014(self):
        """Testing failure with wrong password."""
        logger.info("Testing failure with wrong password...")
        connect_kwargs = {}
        if self.connection_params["use_wallet"]:
            connect_kwargs = {
                "config_dir": self.connection_params["wallet_location"],
                "wallet_location": self.connection_params["wallet_location"],
                "wallet_password": self.connection_params["wallet_password"],
            }
        with pytest.raises(oracledb.DatabaseError):
            select_ai.connect(
                user=self.connection_params["user"],
                password="wrong_pass",
                dsn=self.connection_params["dsn"],
                **connect_kwargs
            )
        logger.info("Correctly raised DatabaseError for wrong password")

    def test_1015(self):
        """Testing connection with bad string."""
        logger.info("Testing connection with bad string...")
        with pytest.raises(TypeError) as e:
            select_ai.connect("not a valid connect string!!")
        assert "missing 2 required positional arguments" in str(e.value)
        logger.info("Correctly raised TypeError for bad string")

    def test_1016(self):
        """Testing connection with bad DSN."""
        logger.info("Testing connection with bad DSN...")
        with pytest.raises(oracledb.DatabaseError) as excinfo:
            select_ai.connect(
                user=self.connection_params["user"],
                password=self.connection_params["password"],
                dsn="invalid_dsn",
                **self.connection_params["connect_kwargs"]
            )
        msg = str(excinfo.value)
        logger.info(f"Database exception message was: {msg}")
        assert ("DPY-4026" in msg) or ("DPY-4027" in msg)
        logger.info("Correctly raised DatabaseError for bad DSN")

    def test_1017(self):
        """Testing connection with bad password."""
        logger.info("Testing connection with bad password...")
        with pytest.raises(oracledb.DatabaseError) as excinfo:
            select_ai.connect(
                user=self.connection_params["user"],
                password=self.connection_params["password"] + "X",
                dsn=self.connection_params["dsn"],
                **self.connection_params["connect_kwargs"]
            )
        assert "ORA-01017" in str(excinfo.value)
        logger.info("Correctly raised DatabaseError for wrong password")

    def test_1018(self):
        """Testing simple query execution."""
        logger.info("Testing simple query execution...")
        test_env.create_connection(use_wallet=self.connection_params["use_wallet"])
        with select_ai.cursor() as cr:
            cr.execute("SELECT 1 FROM DUAL")
            result = cr.fetchone()
            assert result[0] == 1
            logger.info(f"Query executed successfully, result: {result[0]}")
        # select_ai.disconnect()

    def test_1019(self):
        """Testing query with parameters."""
        logger.info("Testing query with parameters...")
        with select_ai.cursor() as cr:
            cr.execute("SELECT :val FROM dual", val=42)
            result = cr.fetchone()
            assert result[0] == 42
            logger.info(f"Query with parameters successful, result: {result[0]}")

    def test_1020(self):
        """Testing fetchall."""
        logger.info("Testing fetchall...")
        with select_ai.cursor() as cursor:
            cursor.execute("SELECT level FROM dual CONNECT BY level <= 5")
            results = cursor.fetchall()
            assert len(results) == 5
            logger.info(f"Fetched rows: {len(results)}")

    def test_1021(self):
        """Testing invalid query."""
        logger.info("Testing invalid query...")
        with select_ai.cursor() as cursor:
            with pytest.raises(oracledb.DatabaseError):
                cursor.execute("SELECT * FROM non_existent_table")
            logger.info("Correctly raised DatabaseError for invalid query")

    def test_1022(self):
        """Testing commit and rollback."""
        logger.info("Testing commit and rollback...")
        with select_ai.cursor() as cursor:
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
            cursor.execute("truncate table test_cr_tab")
            cursor.execute("insert into test_cr_tab values (1)")
            cursor.execute("rollback")
            cursor.execute("select count(*) from test_cr_tab")
            (count,) = cursor.fetchone()
            assert count == 0
            logger.info("Rollback verified successfully")

    def test_1023(self):
        """Testing connection close error."""
        logger.info("Testing connection close error...")
        select_ai.disconnect()
        with pytest.raises(DatabaseNotConnectedError):
            with select_ai.cursor() as cr:
                cr.execute("SELECT 1 FROM DUAL")
        logger.info("DatabaseNotConnectedError correctly raised on disconnected cursor")

    def test_1024(self):
        """Testing repeated disconnect."""
        logger.info("Testing repeated disconnect...")
        test_env.create_connection(use_wallet=self.connection_params["use_wallet"])
        select_ai.disconnect()
        select_ai.disconnect()
        is_connected = select_ai.is_connected()
        assert not is_connected, "Connection should be closed after repeated disconnects"
        logger.info("Repeated disconnect handled successfully")

    def test_1025(self):
        """Testing DBMS_OUTPUT package."""
        logger.info("Testing DBMS_OUTPUT package...")
        test_env.create_connection(use_wallet=self.connection_params["use_wallet"])
        test_string = "Testing DBMS_OUTPUT package"
        with select_ai.cursor() as cursor:
            cursor.callproc("dbms_output.enable")
            cursor.callproc("dbms_output.put_line", [test_string])
            string_var = cursor.var(str)
            number_var = cursor.var(int)
            cursor.callproc("dbms_output.get_line", (string_var, number_var))
            assert string_var.getvalue() == test_string
            logger.info(f"DBMS_OUTPUT verified: {string_var.getvalue()}")
        # select_ai.disconnect()

    def test_1026(self):
        """Testing instance name retrieval."""
        logger.info("Testing instance name retrieval...")
        with select_ai.cursor() as cursor:
            cursor.execute(
                "select upper(sys_context('userenv', 'instance_name')) from dual"
            )
            (instance_name,) = cursor.fetchone()
            assert isinstance(instance_name, str)
            logger.info(f"Instance name: {instance_name}")

    def test_1027(self):
        """Testing max open cursors."""
        logger.info("Testing max open cursors...")
        with select_ai.cursor() as cursor:
            cursor.execute(
                "select value from V$PARAMETER where name='open_cursors'"
            )
            (max_open_cursors,) = cursor.fetchone()
        assert int(max_open_cursors) == 1000
        logger.info(f"Max open cursors: {max_open_cursors}")

    def test_1028(self):
        """Testing service name retrieval."""
        logger.info("Testing service name retrieval...")
        with select_ai.cursor() as cursor:
            cursor.execute(
                "select sys_context('userenv', 'service_name') from dual"
            )
            (service_name,) = cursor.fetchone()
        assert isinstance(service_name, str)
        logger.info(f"Service name: {service_name}")

    def test_1029(self):
        """Testing user and table creation."""
        logger.info("Testing user and table creation...")
        test_username = "TEST_USER1"
        test_password = self.connection_params["password"]
        with select_ai.cursor() as admin_cursor:
            try:
                admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            except oracledb.DatabaseError:
                logger.info(f"User {test_username} did not exist before test")
            admin_cursor.execute(f"CREATE USER {test_username} IDENTIFIED BY {test_password}")
            admin_cursor.execute(f"grant create session, create table, unlimited tablespace to {test_username}")
            logger.info(f"Created test user: {test_username}")
        test_env.create_connection(
            user=test_username,
            password=test_password,
            dsn=self.connection_params["dsn"],
            use_wallet=self.connection_params["use_wallet"]
        )
        with select_ai.cursor() as test_cursor:
            test_cursor.execute("CREATE TABLE test_table (id INT)")
            test_cursor.execute("INSERT INTO test_table (id) VALUES (100)")
            test_cursor.execute("SELECT id FROM test_table")
            result = test_cursor.fetchone()
            assert result[0] == 100
            logger.info("Test table created and verified successfully")
        select_ai.disconnect()
        test_env.create_connection(use_wallet=self.connection_params["use_wallet"])
        with select_ai.cursor() as admin_cursor:
            admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            logger.info(f"Dropped test user: {test_username}")
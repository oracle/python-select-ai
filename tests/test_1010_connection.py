# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import logging

import oracledb
import pytest
import select_ai
from select_ai.errors import DatabaseNotConnectedError

logger = logging.getLogger("TestConnection")


@pytest.fixture(scope="module")
def oci_credential():
    """
    These connection tests do not use the shared OCI credential fixture.
    Override it locally so the module only depends on DB connectivity.
    """
    return None


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )


@pytest.fixture(scope="class")
def connection_params(request, test_env):
    params = {
        "user": test_env.test_user,
        "password": test_env.test_user_password,
        "dsn": test_env.connect_string,
        "wallet_location": test_env.wallet_location,
        "wallet_password": test_env.wallet_password,
        "admin_user": test_env.admin_user,
        "admin_password": test_env.admin_password,
    }
    request.cls.connection_params = params


@pytest.fixture(scope="class")
def connect_as(test_env):
    def _connect_as(*, admin=False, **overrides):
        select_ai.disconnect()
        if admin:
            connect_kwargs = dict(test_env.connect_params(admin=True))
        else:
            connect_kwargs = dict(test_env.connect_params())
        connect_kwargs.update(overrides)
        select_ai.connect(**connect_kwargs)

    return _connect_as


@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown(request, connection_params, connect_as):
    logger.info("=== Setting up TestConnection class ===")
    request.cls.connect_as = staticmethod(connect_as)
    connect_as()
    assert select_ai.is_connected(), "Connection to DB failed"
    logger.info("Initial connection successful")
    yield
    logger.info("=== Tearing down TestConnection class ===")
    try:
        connect_as()
        logger.info("Restored default DB connection")
    except Exception as exc:
        logger.warning("Warning: disconnect failed (%s)", exc)


@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    yield
    if request.instance is not None:
        request.instance.connect_as()
    logger.info("--- Finished test: %s ---", request.function.__name__)

@pytest.mark.usefixtures("connection_params", "setup_and_teardown")
class TestConnection:
    def test_1011(self):
        """Testing connection success with wallet."""
        logger.info("Testing connection success with wallet...")
        self.connect_as()
        assert select_ai.is_connected(), "Connection to DB failed"
        logger.info("Connection successful")
        select_ai.disconnect()
        assert not select_ai.is_connected()
        logger.info("Disconnected after test_1011")

    def test_1012(self):
        """Testing connection without wallet."""
        logger.info("Testing connection without wallet...")
        if self.connection_params["wallet_location"]:
            with pytest.raises(oracledb.DatabaseError, match=r"DPY-4027"):
                select_ai.disconnect()
                select_ai.connect(
                    user=self.connection_params["user"],
                    password=self.connection_params["password"],
                    dsn=self.connection_params["dsn"],
                )
            logger.info("Wallet-less connect correctly failed in wallet-based setup.")
        else:
            select_ai.disconnect()
            select_ai.connect(
                user=self.connection_params["user"],
                password=self.connection_params["password"],
                dsn=self.connection_params["dsn"],
            )
            assert select_ai.is_connected(), "Connection to DB failed without wallet"
            logger.info("Connection successful without wallet")
            select_ai.disconnect()
            assert not select_ai.is_connected()
            logger.info("Disconnected after test_1012")

    def test_1013(self):
        """Testing is_connected returns bool."""
        logger.info("Testing is_connected returns bool...")
        self.connect_as()
        assert isinstance(select_ai.is_connected(), bool)
        select_ai.disconnect()
        logger.info("is_connected check complete and disconnected")

    def test_1014(self):
        """Testing failure with wrong password."""
        logger.info("Testing failure with wrong password...")
        connect_kwargs = {}
        if self.connection_params["wallet_location"]:
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
        connect_kwargs = {}
        if self.connection_params["wallet_location"]:
            connect_kwargs = {
                "config_dir": self.connection_params["wallet_location"],
                "wallet_location": self.connection_params["wallet_location"],
                "wallet_password": self.connection_params["wallet_password"],
            }
        with pytest.raises(oracledb.DatabaseError) as excinfo:
            select_ai.connect(
                user=self.connection_params["user"],
                password=self.connection_params["password"],
                dsn="invalid_dsn",
                **connect_kwargs
            )
        msg = str(excinfo.value)
        logger.info("Database exception message was: %s", msg)
        assert ("DPY-4000" in msg) or ("DPY-4026" in msg) or ("DPY-4027" in msg)
        logger.info("Correctly raised DatabaseError for bad DSN")

    def test_1017(self):
        """Testing connection with bad password."""
        logger.info("Testing connection with bad password...")
        connect_kwargs = {}
        if self.connection_params["wallet_location"]:
            connect_kwargs = {
                "config_dir": self.connection_params["wallet_location"],
                "wallet_location": self.connection_params["wallet_location"],
                "wallet_password": self.connection_params["wallet_password"],
            }
        with pytest.raises(oracledb.DatabaseError) as excinfo:
            select_ai.connect(
                user=self.connection_params["user"],
                password=self.connection_params["password"] + "X",
                dsn=self.connection_params["dsn"],
                **connect_kwargs
            )
        assert "ORA-01017" in str(excinfo.value)
        logger.info("Correctly raised DatabaseError for wrong password")

    def test_1018(self):
        """Testing simple query execution."""
        logger.info("Testing simple query execution...")
        self.connect_as()
        with select_ai.cursor() as cr:
            cr.execute("SELECT 1 FROM DUAL")
            result = cr.fetchone()
            assert result[0] == 1
            logger.info("Query executed successfully, result: %s", result[0])

    def test_1019(self):
        """Testing query with parameters."""
        logger.info("Testing query with parameters...")
        with select_ai.cursor() as cr:
            cr.execute("SELECT :val FROM dual", val=42)
            result = cr.fetchone()
            assert result[0] == 42
            logger.info("Query with parameters successful, result: %s", result[0])

    def test_1020(self):
        """Testing fetchall."""
        logger.info("Testing fetchall...")
        with select_ai.cursor() as cursor:
            cursor.execute("SELECT level FROM dual CONNECT BY level <= 5")
            results = cursor.fetchall()
            assert len(results) == 5
            logger.info("Fetched rows: %s", len(results))

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
        self.connect_as()
        select_ai.disconnect()
        select_ai.disconnect()
        assert not select_ai.is_connected()
        logger.info("Repeated disconnect handled successfully")

    def test_1025(self):
        """Testing DBMS_OUTPUT package."""
        logger.info("Testing DBMS_OUTPUT package...")
        self.connect_as()
        test_string = "Testing DBMS_OUTPUT package"
        with select_ai.cursor() as cursor:
            cursor.callproc("dbms_output.enable")
            cursor.callproc("dbms_output.put_line", [test_string])
            string_var = cursor.var(str)
            number_var = cursor.var(int)
            cursor.callproc("dbms_output.get_line", (string_var, number_var))
            assert string_var.getvalue() == test_string
            logger.info("DBMS_OUTPUT verified: %s", string_var.getvalue())

    def test_1026(self):
        """Testing instance name retrieval."""
        logger.info("Testing instance name retrieval...")
        with select_ai.cursor() as cursor:
            cursor.execute(
                "select upper(sys_context('userenv', 'instance_name')) from dual"
            )
            (instance_name,) = cursor.fetchone()
            assert isinstance(instance_name, str)
            logger.info("Instance name: %s", instance_name)

    def test_1027(self):
        """Testing max open cursors."""
        logger.info("Testing max open cursors...")
        self.connect_as(admin=True)
        with select_ai.cursor() as cursor:
            cursor.execute(
                "select value from V$PARAMETER where name='open_cursors'"
            )
            (max_open_cursors,) = cursor.fetchone()
        assert int(max_open_cursors) == 1000
        logger.info("Max open cursors: %s", max_open_cursors)

    def test_1028(self):
        """Testing service name retrieval."""
        logger.info("Testing service name retrieval...")
        with select_ai.cursor() as cursor:
            cursor.execute(
                "select sys_context('userenv', 'service_name') from dual"
            )
            (service_name,) = cursor.fetchone()
        assert isinstance(service_name, str)
        logger.info("Service name: %s", service_name)

    def test_1029(self):
        """Testing user and table creation."""
        logger.info("Testing user and table creation...")
        test_username = "TEST_USER1"
        test_password = self.connection_params["password"]
        self.connect_as(admin=True)
        with select_ai.cursor() as admin_cursor:
            try:
                admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            except oracledb.DatabaseError:
                logger.info("User %s did not exist before test", test_username)
            admin_cursor.execute(
                f'CREATE USER {test_username} IDENTIFIED BY "{test_password}"'
            )
            admin_cursor.execute(
                f"grant create session, create table, unlimited tablespace to {test_username}"
            )
        logger.info("Created test user: %s", test_username)
        self.connect_as(
            user=test_username,
            password=test_password,
            dsn=self.connection_params["dsn"],
        )
        with select_ai.cursor() as test_cursor:
            test_cursor.execute("CREATE TABLE test_table (id INT)")
            test_cursor.execute("INSERT INTO test_table (id) VALUES (100)")
            test_cursor.execute("SELECT id FROM test_table")
            result = test_cursor.fetchone()
            assert result[0] == 100
            logger.info("Test table created and verified successfully")
        self.connect_as(admin=True)
        with select_ai.cursor() as admin_cursor:
            admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            logger.info("Dropped test user: %s", test_username)

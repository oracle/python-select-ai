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

logger = logging.getLogger("TestAsyncConnection")

pytestmark = pytest.mark.anyio


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
    }
    request.cls.connection_params = params


@pytest.fixture(scope="class")
def async_connect_as(test_env):
    async def _connect_as(*, admin=False, **overrides):
        await select_ai.async_disconnect()
        if admin:
            connect_kwargs = dict(test_env.connect_params(admin=True))
        else:
            connect_kwargs = dict(test_env.connect_params())
        connect_kwargs.update(overrides)
        await select_ai.async_connect(**connect_kwargs)

    return _connect_as


@pytest.fixture(scope="class", autouse=True)
async def setup_and_teardown(
    request, async_connect, connection_params, async_connect_as
):
    logger.info("=== Setting up TestAsyncConnection class ===")
    request.cls.async_connect_as = staticmethod(async_connect_as)
    await async_connect_as()
    assert await select_ai.async_is_connected(), "Connection to DB failed"
    logger.info("Initial connection successful")
    yield
    logger.info("=== Tearing down TestAsyncConnection class ===")
    try:
        await async_connect_as()
        logger.info("Restored default DB connection")
    except Exception as exc:
        logger.warning("Warning: disconnect failed (%s)", exc)


@pytest.fixture(autouse=True)
async def log_test_name(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    yield
    if request.instance is not None:
        await request.instance.async_connect_as()
    logger.info("--- Finished test: %s ---", request.function.__name__)


@pytest.mark.usefixtures("connection_params", "setup_and_teardown")
class TestAsyncConnection:
    async def test_1011(self):
        """Testing connection success with wallet."""
        logger.info("Testing connection success with wallet...")
        await self.async_connect_as()
        assert await select_ai.async_is_connected(), "Connection to DB failed"
        logger.info("Connection successful")
        await select_ai.async_disconnect()
        assert not await select_ai.async_is_connected()
        logger.info("Disconnected after test_1011")

    async def test_1012(self):
        """Testing connection without wallet."""
        logger.info("Testing connection without wallet...")
        if self.connection_params["wallet_location"]:
            with pytest.raises(oracledb.DatabaseError, match=r"DPY-4027"):
                await select_ai.async_disconnect()
                await select_ai.async_connect(
                    user=self.connection_params["user"],
                    password=self.connection_params["password"],
                    dsn=self.connection_params["dsn"],
                )
            logger.info(
                "Wallet-less connect correctly failed in wallet-based setup."
            )
        else:
            await select_ai.async_disconnect()
            await select_ai.async_connect(
                user=self.connection_params["user"],
                password=self.connection_params["password"],
                dsn=self.connection_params["dsn"],
            )
            assert await select_ai.async_is_connected(), (
                "Connection to DB failed without wallet"
            )
            logger.info("Connection successful without wallet")
            await select_ai.async_disconnect()
            assert not await select_ai.async_is_connected()
            logger.info("Disconnected after test_1012")

    async def test_1013(self):
        """Testing is_connected returns bool."""
        logger.info("Testing is_connected returns bool...")
        await self.async_connect_as()
        assert isinstance(await select_ai.async_is_connected(), bool)
        await select_ai.async_disconnect()
        logger.info("is_connected check complete and disconnected")

    async def test_1014(self):
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
            await select_ai.async_connect(
                user=self.connection_params["user"],
                password="wrong_pass",
                dsn=self.connection_params["dsn"],
                **connect_kwargs,
            )
        logger.info("Correctly raised DatabaseError for wrong password")

    async def test_1015(self):
        """Testing connection with bad string."""
        logger.info("Testing connection with bad string...")
        with pytest.raises(TypeError) as exc_info:
            await select_ai.async_connect("not a valid connect string!!")
        assert "missing 2 required positional arguments" in str(exc_info.value)
        logger.info("Correctly raised TypeError for bad string")

    async def test_1016(self):
        """Testing connection with bad DSN."""
        logger.info("Testing connection with bad DSN...")
        connect_kwargs = {}
        if self.connection_params["wallet_location"]:
            connect_kwargs = {
                "config_dir": self.connection_params["wallet_location"],
                "wallet_location": self.connection_params["wallet_location"],
                "wallet_password": self.connection_params["wallet_password"],
            }
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_connect(
                user=self.connection_params["user"],
                password=self.connection_params["password"],
                dsn="invalid_dsn",
                **connect_kwargs,
            )
        msg = str(exc_info.value)
        logger.info("Database exception message was: %s", msg)
        assert ("DPY-4000" in msg) or ("DPY-4026" in msg) or ("DPY-4027" in msg)
        logger.info("Correctly raised DatabaseError for bad DSN")

    async def test_1017(self):
        """Testing connection with bad password."""
        logger.info("Testing connection with bad password...")
        connect_kwargs = {}
        if self.connection_params["wallet_location"]:
            connect_kwargs = {
                "config_dir": self.connection_params["wallet_location"],
                "wallet_location": self.connection_params["wallet_location"],
                "wallet_password": self.connection_params["wallet_password"],
            }
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_connect(
                user=self.connection_params["user"],
                password=self.connection_params["password"] + "X",
                dsn=self.connection_params["dsn"],
                **connect_kwargs,
            )
        assert "ORA-01017" in str(exc_info.value)
        logger.info("Correctly raised DatabaseError for wrong password")

    async def test_1018(self):
        """Testing simple query execution."""
        logger.info("Testing simple query execution...")
        await self.async_connect_as()
        async with select_ai.async_cursor() as cr:
            await cr.execute("SELECT 1 FROM DUAL")
            result = await cr.fetchone()
        assert result[0] == 1
        logger.info("Query executed successfully, result: %s", result[0])

    async def test_1019(self):
        """Testing query with parameters."""
        logger.info("Testing query with parameters...")
        async with select_ai.async_cursor() as cr:
            await cr.execute("SELECT :val FROM dual", val=42)
            result = await cr.fetchone()
        assert result[0] == 42
        logger.info("Query with parameters successful, result: %s", result[0])

    async def test_1020(self):
        """Testing fetchall."""
        logger.info("Testing fetchall...")
        async with select_ai.async_cursor() as cursor:
            await cursor.execute("SELECT level FROM dual CONNECT BY level <= 5")
            results = await cursor.fetchall()
        assert len(results) == 5
        logger.info("Fetched rows: %s", len(results))

    async def test_1021(self):
        """Testing invalid query."""
        logger.info("Testing invalid query...")
        async with select_ai.async_cursor() as cursor:
            with pytest.raises(oracledb.DatabaseError):
                await cursor.execute("SELECT * FROM non_existent_table")
        logger.info("Correctly raised DatabaseError for invalid query")

    async def test_1022(self):
        """Testing commit and rollback."""
        logger.info("Testing commit and rollback...")
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                """
                begin
                    execute immediate 'create table test_cr_tab_async (id int)';
                exception
                    when others then
                        if sqlcode != -955 then
                            raise;
                        end if;
                end;
                """
            )
        async with select_ai.db.async_get_connection() as async_connection:
            await async_connection.commit()
        async with select_ai.async_cursor() as cursor:
            await cursor.execute("truncate table test_cr_tab_async")
            await cursor.execute("insert into test_cr_tab_async values (1)")
        async with select_ai.db.async_get_connection() as async_connection:
            await async_connection.rollback()
        async with select_ai.async_cursor() as cursor:
            await cursor.execute("select count(*) from test_cr_tab_async")
            (count,) = await cursor.fetchone()
        assert count == 0
        logger.info("Rollback verified successfully")

    async def test_1023(self):
        """Testing connection close error."""
        logger.info("Testing connection close error...")
        await select_ai.async_disconnect()
        with pytest.raises(DatabaseNotConnectedError):
            async with select_ai.async_cursor() as cr:
                await cr.execute("SELECT 1 FROM DUAL")
        logger.info(
            "DatabaseNotConnectedError correctly raised on disconnected cursor"
        )

    async def test_1024(self):
        """Testing repeated disconnect."""
        logger.info("Testing repeated disconnect...")
        await self.async_connect_as()
        await select_ai.async_disconnect()
        await select_ai.async_disconnect()
        assert not await select_ai.async_is_connected()
        logger.info("Repeated disconnect handled successfully")

    async def test_1025(self):
        """Testing DBMS_OUTPUT package."""
        logger.info("Testing DBMS_OUTPUT package...")
        await self.async_connect_as()
        test_string = "Testing DBMS_OUTPUT package"
        async with select_ai.async_cursor() as cursor:
            await cursor.callproc("dbms_output.enable")
            await cursor.callproc("dbms_output.put_line", [test_string])
            string_var = cursor.var(str)
            number_var = cursor.var(int)
            await cursor.callproc("dbms_output.get_line", (string_var, number_var))
        assert string_var.getvalue() == test_string
        logger.info("DBMS_OUTPUT verified: %s", string_var.getvalue())

    async def test_1026(self):
        """Testing instance name retrieval."""
        logger.info("Testing instance name retrieval...")
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                "select upper(sys_context('userenv', 'instance_name')) from dual"
            )
            (instance_name,) = await cursor.fetchone()
        assert isinstance(instance_name, str)
        logger.info("Instance name: %s", instance_name)

    async def test_1027(self):
        """Testing max open cursors."""
        logger.info("Testing max open cursors...")
        await self.async_connect_as(admin=True)
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                "select value from V$PARAMETER where name='open_cursors'"
            )
            (max_open_cursors,) = await cursor.fetchone()
        assert int(max_open_cursors) == 1000
        logger.info("Max open cursors: %s", max_open_cursors)

    async def test_1028(self):
        """Testing service name retrieval."""
        logger.info("Testing service name retrieval...")
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                "select sys_context('userenv', 'service_name') from dual"
            )
            (service_name,) = await cursor.fetchone()
        assert isinstance(service_name, str)
        logger.info("Service name: %s", service_name)

    async def test_1029(self):
        """Testing user and table creation."""
        logger.info("Testing user and table creation...")
        test_username = "TEST_USER2"
        test_password = self.connection_params["password"]
        await self.async_connect_as(admin=True)
        async with select_ai.async_cursor() as admin_cursor:
            try:
                await admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            except oracledb.DatabaseError:
                logger.info("User %s did not exist before test", test_username)
            await admin_cursor.execute(
                f'CREATE USER {test_username} IDENTIFIED BY "{test_password}"'
            )
            await admin_cursor.execute(
                f"grant create session, create table, unlimited tablespace to {test_username}"
            )
        logger.info("Created test user: %s", test_username)

        await self.async_connect_as(
            user=test_username,
            password=test_password,
            dsn=self.connection_params["dsn"],
        )
        async with select_ai.async_cursor() as test_cursor:
            await test_cursor.execute("CREATE TABLE test_table_async (id INT)")
            await test_cursor.execute(
                "INSERT INTO test_table_async (id) VALUES (100)"
            )
            await test_cursor.execute("SELECT id FROM test_table_async")
            result = await test_cursor.fetchone()
        assert result[0] == 100
        logger.info("Test table created and verified successfully")

        await self.async_connect_as(admin=True)
        async with select_ai.async_cursor() as admin_cursor:
            await admin_cursor.execute(f"DROP USER {test_username} CASCADE")
        logger.info("Dropped test user: %s", test_username)

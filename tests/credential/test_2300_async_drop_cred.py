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

logger = logging.getLogger("TestAsyncDropCredential")

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="class")
def drop_params(request, credential_test_params):
    request.cls.drop_params = credential_test_params


@pytest.fixture(scope="class", autouse=True)
async def setup_and_teardown(
    request,
    async_connect,
    drop_params,
    test_env,
):
    logger.info("=== Setting up TestAsyncDropCredential class ===")
    assert await select_ai.async_is_connected(), "Connection to DB failed"
    request.cls.test_env = test_env
    logger.info("Initial connection successful")
    yield
    logger.info("=== Tearing down TestAsyncDropCredential class ===")
    logger.info("Connection cleanup is owned by root session fixtures.")


@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    yield
    logger.info("--- Finished test: %s ---", request.function.__name__)


@pytest.mark.usefixtures("drop_params", "setup_and_teardown")
class TestAsyncDropCredential:
    @staticmethod
    def get_cred_param(params, cred_name=None):
        logger.info("Preparing credential params for: %s", cred_name)
        return dict(
            credential_name=cred_name,
            username=params["cred_username"],
            password=params["cred_password"],
        )

    @classmethod
    async def create_test_credential(cls, cred_name="GENAI_CRED"):
        logger.info("Creating test credential: %s", cred_name)
        credential = cls.get_cred_param(cls.drop_params, cred_name)
        try:
            await select_ai.async_create_credential(
                credential=credential,
                replace=False,
            )
            logger.info("Credential '%s' created successfully.", cred_name)
        except Exception as exc:
            pytest.fail(
                f"async_create_credential() raised {exc} unexpectedly."
            )

    @classmethod
    async def create_local_user(cls, test_username="TEST_USER1"):
        logger.info("Creating local user: %s", test_username)
        test_password = cls.drop_params["password"]
        escaped_password = test_password.replace('"', '""')
        admin_conn = await oracledb.connect_async(
            **cls.test_env.connect_params(admin=True)
        )
        try:
            async with admin_conn.cursor() as admin_cursor:
                try:
                    await admin_cursor.execute(f"DROP USER {test_username} CASCADE")
                except oracledb.DatabaseError:
                    pass
                await admin_cursor.execute(
                    f'CREATE USER {test_username} IDENTIFIED BY "{escaped_password}"'
                )
                await admin_cursor.execute(
                    "grant create session, create table, unlimited tablespace "
                    f"to {test_username}"
                )
                await admin_cursor.execute(
                    f"grant execute on dbms_cloud to {test_username}"
                )
            await admin_conn.commit()
        finally:
            await admin_conn.close()
        logger.info("Local user '%s' ready.", test_username)

    @classmethod
    async def drop_local_user(cls, test_username="TEST_USER1"):
        admin_conn = await oracledb.connect_async(
            **cls.test_env.connect_params(admin=True)
        )
        try:
            async with admin_conn.cursor() as admin_cursor:
                await admin_cursor.execute(f"DROP USER {test_username} CASCADE")
            await admin_conn.commit()
        finally:
            await admin_conn.close()

    @classmethod
    def local_user_connect_params(cls, test_username, test_password):
        connect_params = cls.test_env.connect_params()
        connect_params.update(user=test_username, password=test_password)
        return connect_params

    async def test_2301(self):
        """Deleting existing credential (force=True)."""
        await self.create_test_credential()
        try:
            await select_ai.async_delete_credential("GENAI_CRED", force=True)
            logger.info("Credential deleted successfully.")
        except Exception as exc:
            pytest.fail(f"async_delete_credential() raised {exc} unexpectedly.")

    async def test_2302(self):
        """Deleting same credential twice (force=True)."""
        await self.create_test_credential()
        await select_ai.async_delete_credential("GENAI_CRED", force=True)
        await select_ai.async_delete_credential("GENAI_CRED", force=True)
        logger.info("Double deletion succeeded (force=True).")

    async def test_2303(self):
        """Deleting same credential twice (force=False)."""
        await self.create_test_credential()
        await select_ai.async_delete_credential("GENAI_CRED", force=False)
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_delete_credential("GENAI_CRED", force=False)
        logger.info(
            "Expected DatabaseError for second delete (force=False): %s",
            exc_info.value,
        )

    async def test_2304(self):
        """Deleting nonexistent credential (default force=False)."""
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_delete_credential("nonexistent_cred")
        logger.info(
            "Expected DatabaseError for nonexistent credential: %s",
            exc_info.value,
        )

    async def test_2305(self):
        """Deleting nonexistent credential (force=False)."""
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_delete_credential(
                "nonexistent_cred",
                force=False,
            )
        logger.info(
            "Expected DatabaseError for nonexistent credential: %s",
            exc_info.value,
        )

    async def test_2306(self):
        """Deleting nonexistent credential (force=True)."""
        try:
            await select_ai.async_delete_credential(
                "nonexistent_cred",
                force=True,
            )
            logger.info("No error raised (expected behavior).")
        except Exception as exc:
            pytest.fail(
                f"async_delete_credential(force=True) raised {exc} unexpectedly."
            )

    async def test_2307(self):
        """Deleting credential as local user."""
        test_username = "TEST_USER1"
        await self.create_local_user(test_username)
        credential = self.get_cred_param(self.drop_params, "GENAI_CRED_USER1")
        try:
            user_conn = await oracledb.connect_async(
                **self.local_user_connect_params(
                    test_username,
                    self.drop_params["password"],
                )
            )
            try:
                async with user_conn.cursor() as cursor:
                    await cursor.callproc(
                        "DBMS_CLOUD.CREATE_CREDENTIAL",
                        keyword_parameters=credential,
                    )
                    await cursor.callproc(
                        "DBMS_CLOUD.DROP_CREDENTIAL",
                        keyword_parameters={
                            "credential_name": "GENAI_CRED_USER1"
                        },
                    )
                await user_conn.commit()
            finally:
                await user_conn.close()
            logger.info("Local user credential deleted successfully.")
        except Exception as exc:
            pytest.fail(f"async_delete_credential() raised {exc} unexpectedly.")
        finally:
            await self.drop_local_user(test_username)
            logger.info("Local user cleanup complete.")

    async def test_2308(self):
        """Deleting credential with invalid name."""
        with pytest.raises(
            oracledb.DatabaseError,
            match=r"ORA-20010: Invalid credential name",
        ):
            await select_ai.async_delete_credential("invalid!@#", force=True)
        logger.info("Caught expected ORA-20010 for invalid name.")

    async def test_2309(self):
        """Deleting credential without active connection."""
        await select_ai.async_disconnect()
        try:
            with pytest.raises(select_ai.errors.DatabaseNotConnectedError) as exc_info:
                await select_ai.async_delete_credential("GENAI_CRED", force=True)
            logger.info(
                "Expected DatabaseNotConnectedError raised: %s",
                exc_info.value,
            )
        finally:
            select_ai.create_pool_async(**self.test_env.connect_params(use_pool=True))

    async def test_2310(self):
        """Deleting credential with name exceeding max length."""
        long_name = "GENAI_CRED_" + "a" * 120
        with pytest.raises(
            oracledb.DatabaseError,
            match=(
                r"ORA-20008: Credential name length .* exceeds maximum length"
            ),
        ):
            await select_ai.async_delete_credential(long_name, force=True)
        logger.info("Caught expected ORA-20008 for long credential name.")

    async def test_2311(self):
        """Deleting credential with lowercase name."""
        await self.create_test_credential("GENAI_CRED")
        try:
            await select_ai.async_delete_credential(credential_name="genai_cred")
            logger.info(
                "Credential deleted successfully (case-insensitive)."
            )
        except Exception as exc:
            pytest.fail(
                "async_delete_credential raised "
                f"{exc} unexpectedly for lowercase name"
            )

    async def test_2312(self):
        """Deleting credential with empty or None name."""
        with pytest.raises(
            oracledb.DatabaseError,
            match=r"ORA-20010: Missing credential name",
        ):
            await select_ai.async_delete_credential(
                credential_name="",
                force=True,
            )
        with pytest.raises(
            oracledb.DatabaseError,
            match=r"ORA-20010: Missing credential name",
        ):
            await select_ai.async_delete_credential(
                credential_name=None,
                force=True,
            )
        logger.info("Caught expected ORA-20010 for missing credential name.")

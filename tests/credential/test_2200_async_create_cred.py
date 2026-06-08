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

logger = logging.getLogger("TestAsyncCreateCredential")

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="class")
def credential_params(request, credential_test_params):
    request.cls.credential_params = credential_test_params


@pytest.fixture(scope="class", autouse=True)
async def setup_and_teardown_cred(
    request,
    async_connect,
    credential_params,
    test_env,
):
    logger.info("=== Setting up TestAsyncCreateCredential class ===")
    assert await select_ai.async_is_connected(), "Connection to DB failed"
    request.cls.test_env = test_env
    logger.info("Initial connection successful")
    yield
    logger.info("=== Tearing down TestAsyncCreateCredential class ===")
    logger.info("Connection cleanup is owned by root session fixtures.")


@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    yield
    logger.info("--- Finished test: %s ---", request.function.__name__)


@pytest.mark.usefixtures("credential_params", "setup_and_teardown_cred")
class TestAsyncCreateCredential:
    @staticmethod
    def get_native_cred_param(params, cred_name=None):
        return dict(
            credential_name=cred_name,
            user_ocid=params["user_ocid"],
            tenancy_ocid=params["tenancy_ocid"],
            private_key=params["private_key"],
            fingerprint=params["fingerprint"],
        )

    @staticmethod
    def get_cred_param(params, cred_name=None):
        return dict(
            credential_name=cred_name,
            username=params["cred_username"],
            password=params["cred_password"],
        )

    @staticmethod
    async def drop_credential(cred_name="GENAI_CRED"):
        logger.info("Dropping credential: %s", cred_name)
        await select_ai.async_delete_credential(cred_name, force=True)
        logger.info("Dropped credential: %s", cred_name)

    @classmethod
    async def create_local_user(cls, test_username="TEST_USER1"):
        test_password = cls.credential_params["password"]
        escaped_password = test_password.replace('"', '""')
        admin_conn = await oracledb.connect_async(
            **cls.test_env.connect_params(admin=True)
        )
        try:
            async with admin_conn.cursor() as admin_cursor:
                try:
                    await admin_cursor.execute(f"DROP USER {test_username} CASCADE")
                except oracledb.DatabaseError:
                    logger.info(
                        "User '%s' did not exist, continuing...",
                        test_username,
                    )
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

    async def test_2201(self):
        """Testing basic credential creation."""
        credential = self.get_cred_param(self.credential_params, "GENAI_CRED")
        logger.info("Creating credential: %s", credential)
        try:
            await select_ai.async_create_credential(
                credential=credential,
                replace=False,
            )
            logger.info("Credential created successfully.")
        except Exception as exc:
            pytest.fail(f"async_create_credential() raised {exc} unexpectedly.")
        await self.drop_credential()

    async def test_2202(self):
        """Testing creating credential twice without replace."""
        credential = self.get_cred_param(self.credential_params, "GENAI_CRED")
        try:
            await select_ai.async_create_credential(credential=credential)
            logger.info("First credential creation successful.")
        except Exception as exc:
            pytest.fail(f"async_create_credential() raised {exc} unexpectedly.")
        logger.info("Attempting to create credential again (expected to fail)...")
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_create_credential(credential=credential)
        logger.info("Caught expected DatabaseError: %s", exc_info.value)
        assert "ORA-20022" in str(exc_info.value)
        await self.drop_credential()

    async def test_2203(self):
        """Testing repeated credential creation with replace=True."""
        credential = self.get_cred_param(self.credential_params, "GENAI_CRED")
        for i in range(5):
            logger.info("Creating credential iteration %s...", i + 1)
            await select_ai.async_create_credential(
                credential=credential,
                replace=True,
            )
        logger.info("Repeated creation succeeded.")
        await self.drop_credential()

    async def test_2204(self):
        """Testing credential creation with replace=True."""
        credential = self.get_cred_param(self.credential_params, "GENAI_CRED")
        try:
            await select_ai.async_create_credential(
                credential=credential,
                replace=True,
            )
            logger.info("Credential created successfully with replace=True.")
        except Exception as exc:
            pytest.fail(f"async_create_credential() raised {exc} unexpectedly.")
        await self.drop_credential()

    async def test_2205(self):
        """Testing credential creation twice with replace=True."""
        credential = self.get_cred_param(self.credential_params, "GENAI_CRED")
        try:
            await select_ai.async_create_credential(
                credential=credential,
                replace=True,
            )
            await select_ai.async_create_credential(
                credential=credential,
                replace=True,
            )
            logger.info(
                "Credential created successfully twice with replace=True."
            )
        except Exception as exc:
            pytest.fail(f"async_create_credential() raised {exc} unexpectedly.")
        await self.drop_credential()

    async def test_2206(self):
        """Testing replace=True then replace=False behavior."""
        credential = self.get_cred_param(self.credential_params, "GENAI_CRED")
        try:
            await select_ai.async_create_credential(
                credential=credential,
                replace=True,
            )
            logger.info("First creation succeeded.")
        except Exception as exc:
            pytest.fail(f"async_create_credential() raised {exc} unexpectedly.")
        logger.info("Second creation without replace (expected to fail)...")
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_create_credential(credential=credential)
        logger.info("Caught expected error: %s", exc_info.value)
        assert "ORA-20022" in str(exc_info.value)
        await self.drop_credential()

    async def test_2207(self):
        """Testing replace=False followed by replace=True."""
        credential = self.get_cred_param(self.credential_params, "GENAI_CRED")
        try:
            await select_ai.async_create_credential(credential=credential)
            logger.info("Credential created (replace=False).")
            await select_ai.async_create_credential(
                credential=credential,
                replace=True,
            )
            logger.info("Credential replaced successfully (replace=True).")
        except Exception as exc:
            pytest.fail(f"async_create_credential() raised {exc} unexpectedly.")
        await self.drop_credential()

    async def test_2208(self):
        """Testing native credential creation."""
        credential = self.get_native_cred_param(
            self.credential_params,
            "GENAI_CRED",
        )
        try:
            await select_ai.async_create_credential(
                credential=credential,
                replace=False,
            )
            logger.info("Native credential created successfully.")
        except Exception as exc:
            pytest.fail(f"async_create_credential() raised {exc} unexpectedly.")
        await self.drop_credential()

    async def test_2209(self):
        """Testing native credential creation twice."""
        credential = self.get_native_cred_param(
            self.credential_params,
            "GENAI_CRED",
        )
        try:
            await select_ai.async_create_credential(credential=credential)
            logger.info("First native credential created.")
        except Exception as exc:
            pytest.fail(f"async_create_credential() raised {exc} unexpectedly.")
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_create_credential(credential=credential)
        logger.info("Expected error caught: %s", exc_info.value)
        assert "ORA-20022" in str(exc_info.value)
        await self.drop_credential()

    async def test_2210(self):
        """Testing native credential creation with replace=True."""
        credential = self.get_native_cred_param(
            self.credential_params,
            "GENAI_CRED",
        )
        try:
            await select_ai.async_create_credential(
                credential=credential,
                replace=True,
            )
            logger.info("Native credential created successfully.")
        except Exception as exc:
            pytest.fail(f"async_create_credential() raised {exc} unexpectedly.")
        await self.drop_credential()

    async def test_2211(self):
        """Testing native credential creation with replace=True twice."""
        credential = self.get_native_cred_param(
            self.credential_params,
            "GENAI_CRED",
        )
        for i in range(2):
            logger.info(
                "Creating native credential iteration %s (replace=True)...",
                i + 1,
            )
            await select_ai.async_create_credential(
                credential=credential,
                replace=True,
            )
        logger.info("Native credential replaced successfully twice.")
        await self.drop_credential()

    async def test_2212(self):
        """Testing creation with empty credential name."""
        credential = self.get_cred_param(self.credential_params)
        with pytest.raises(Exception) as exc_info:
            await select_ai.async_create_credential(credential=credential)
        logger.info("Expected exception caught: %s", exc_info.value)
        assert "ORA-20010: Missing credential name" in str(exc_info.value)

    async def test_2213(self):
        """Testing credential creation with empty dictionary."""
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.async_create_credential(credential={})
        logger.info("Expected exception caught: %s", exc_info.value)
        assert (
            "PLS-00306: wrong number or types of arguments in call to "
            "'CREATE_CREDENTIAL'" in str(exc_info.value)
        )

    async def test_2214(self):
        """Testing credential creation with invalid username."""
        credential = dict(
            credential_name="GENAI_CRED",
            username="invalid_username",
            password=self.credential_params["cred_password"],
        )
        await select_ai.async_create_credential(credential=credential, replace=True)
        logger.info("Credential with invalid username created successfully.")
        await self.drop_credential()

    async def test_2215(self):
        """Testing credential creation with invalid password."""
        credential = dict(
            credential_name="GENAI_CRED",
            username=self.credential_params["cred_username"],
            password="invalid_pwd",
        )
        await select_ai.async_create_credential(credential=credential, replace=True)
        logger.info("Credential with invalid password created successfully.")
        await self.drop_credential()

    async def test_2216(self):
        """Testing credential creation when DB is disconnected."""
        await select_ai.async_disconnect()
        credential = self.get_cred_param(self.credential_params, "GENAI_CRED")
        try:
            with pytest.raises(DatabaseNotConnectedError):
                await select_ai.async_create_credential(
                    credential=credential,
                    replace=False,
                )
            logger.info("Expected DatabaseNotConnectedError raised.")
        finally:
            select_ai.create_pool_async(**self.test_env.connect_params(use_pool=True))

    async def test_2217(self):
        """Test Credential creation for a local test user."""
        test_username = "TEST_USER1"
        test_password = self.credential_params["password"]
        credential = self.get_cred_param(
            self.credential_params,
            "GENAI_CRED_USER1",
        )
        try:
            await self.create_local_user(test_username)
            user_conn = await oracledb.connect_async(
                **self.local_user_connect_params(test_username, test_password)
            )
            try:
                async with user_conn.cursor() as cursor:
                    await cursor.callproc(
                        "DBMS_CLOUD.CREATE_CREDENTIAL",
                        keyword_parameters=credential,
                    )
                    logger.info("Credential created successfully.")
                    await cursor.callproc(
                        "DBMS_CLOUD.DROP_CREDENTIAL",
                        keyword_parameters={
                            "credential_name": "GENAI_CRED_USER1"
                        },
                    )
                await user_conn.commit()
            finally:
                await user_conn.close()
        except Exception as exc:
            pytest.fail(f"async_create_credential() raised {exc} unexpectedly.")
        finally:
            await self.drop_local_user(test_username)
            logger.info("Test user '%s' dropped successfully.", test_username)

    async def test_2218(self):
        """Testing credential name with special characters."""
        credential = self.get_cred_param(
            self.credential_params,
            "GENAI_CRED!@#",
        )
        with pytest.raises(
            oracledb.DatabaseError,
            match="ORA-20010: Invalid credential name",
        ):
            await select_ai.async_create_credential(
                credential=credential,
                replace=False,
            )
        logger.info("Invalid name test passed.")

    async def test_2219(self):
        """Testing credential name exceeding 128 characters."""
        long_name = "GENAI_CRED" + "_" + "a" * (128 - len("GENAI_CRED"))
        credential = self.get_cred_param(self.credential_params, long_name)
        with pytest.raises(
            oracledb.DatabaseError,
            match=(
                r"ORA-20008: Credential name length \(129\) exceeds "
                r"maximum length \(128\)"
            ),
        ):
            await select_ai.async_create_credential(
                credential=credential,
                replace=False,
            )
        logger.info("Long credential name test passed.")

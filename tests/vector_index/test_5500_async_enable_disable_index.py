# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import asyncio
import logging
import time

import oracledb
import pytest
import select_ai
from select_ai import AsyncVectorIndex, OracleVectorIndexAttributes

logger = logging.getLogger("TestAsyncEnableDisableVectorIndex")

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="class")
def enabledisable_params(request, vcidx_params):
    request.cls.enabledisable_params = vcidx_params


@pytest.fixture(scope="class", autouse=True)
async def setup_and_teardown(request, async_connect, enabledisable_params):
    logger.info("=== Setting up TestAsyncEnableDisableVectorIndex class ===")
    p = request.cls.enabledisable_params

    assert await select_ai.async_is_connected(), "Connection to DB failed"

    request.cls.user = p["user"]
    request.cls.password = p["password"]
    request.cls.dsn = p["dsn"]
    request.cls.user_ocid = p["user_ocid"]
    request.cls.tenancy_ocid = p["tenancy_ocid"]
    request.cls.private_key = p["private_key"]
    request.cls.fingerprint = p["fingerprint"]
    request.cls.cred_username = p["cred_username"]
    request.cls.cred_password = p["cred_password"]
    request.cls.oci_compartment_id = p["oci_compartment_id"]
    request.cls.embedding_location = p["embedding_location"]

    logger.info("Fetching credential secrets and OCI configuration...")

    async with select_ai.async_cursor() as cursor:
        await cursor.execute(
            "begin execute immediate 'drop table test_items purge'; "
            "exception when others then null; end;"
        )
        await cursor.execute(
            "create table test_items (id number primary key, "
            "name varchar2(50))"
        )
        await cursor.execute("insert into test_items values (1, 'Alpha')")
        await cursor.execute("insert into test_items values (2, 'Beta')")
        await cursor.execute("commit")

    request.cls.genai_cred = p["genai_cred"]
    request.cls.objstore_cred = p["objstore_cred"]
    request.cls.profile_name = p["profile_name"]
    await request.cls.create_credential()
    request.cls.profile = await request.cls.create_profile()
    logger.info("Setup complete.")

    vi_attrs = OracleVectorIndexAttributes(
        location=p["embedding_location"],
        object_storage_credential_name=request.cls.objstore_cred,
    )
    request.cls.vector_index_attributes = vi_attrs
    request.cls.base_index_name = p["enabledisable_index_name"]

    yield

    logger.info("=== Tearing down TestAsyncEnableDisableVectorIndex class ===")
    try:
        await request.cls.profile.delete()
    except Exception as exc:
        logger.warning("profile.delete() raised %s unexpectedly.", exc)

    await request.cls.delete_credential()

    async with select_ai.async_cursor() as cursor:
        await cursor.execute(
            "begin execute immediate 'drop table test_items purge'; "
            "exception when others then null; end;"
        )

    logger.info("Teardown complete.\n")


@pytest.fixture(autouse=True)
async def vector_index_state(request):
    """Create an isolated vector index for each test method."""
    logger.info("--- Starting test: %s ---", request.function.__name__)
    index_name = f"{request.cls.base_index_name}_{request.function.__name__}"
    vector_index = AsyncVectorIndex(
        index_name=index_name,
        attributes=request.cls.vector_index_attributes,
        description="Test vector index",
        profile=request.cls.profile,
    )
    await vector_index.create(replace=True)

    # Test instances, unlike the class, are not shared between test methods.
    request.instance.index_name = index_name
    request.instance.async_vector_index = await AsyncVectorIndex.fetch(
        index_name
    )
    logger.info(request.instance.async_vector_index.index_name)

    try:
        yield
    finally:
        try:
            await request.cls.delete_index_with_retry(
                AsyncVectorIndex(index_name=index_name),
                force=True,
            )
        except Exception as exc:
            logger.warning(
                "Warning: drop vector index %s failed: %s", index_name, exc
            )
        logger.info("--- Finished test: %s ---", request.function.__name__)


@pytest.mark.usefixtures("enabledisable_params", "setup_and_teardown")
class TestAsyncEnableDisableVectorIndex:
    @classmethod
    def get_native_cred_param(cls, cred_name=None) -> dict:
        logger.info("Preparing native credential params for: %s", cred_name)
        p = cls.enabledisable_params
        return dict(
            credential_name=cred_name,
            user_ocid=p["user_ocid"],
            tenancy_ocid=p["tenancy_ocid"],
            private_key=p["private_key"],
            fingerprint=p["fingerprint"],
        )

    @classmethod
    def get_cred_param(cls, cred_name=None) -> dict:
        logger.info("Preparing basic credential params for: %s", cred_name)
        p = cls.enabledisable_params
        return dict(
            credential_name=cred_name,
            username=p["cred_username"],
            password=p["cred_password"],
        )

    @classmethod
    async def create_credential(
        cls,
        genai_cred=None,
        objstore_cred=None,
    ):
        genai_cred = genai_cred or cls.genai_cred
        objstore_cred = objstore_cred or cls.objstore_cred
        logger.info("Creating credentials: %s, %s", genai_cred, objstore_cred)

        genai_credential = cls.get_native_cred_param(genai_cred)
        try:
            logger.info("Creating GenAI credential: %s", genai_cred)
            await select_ai.async_create_credential(
                credential=genai_credential,
                replace=True,
            )
            logger.info("GenAI credential created.")
        except Exception as exc:
            logger.error("create_credential() raised %s unexpectedly.", exc)
            raise AssertionError(
                f"create_credential() raised {exc} unexpectedly."
            )

        p = cls.enabledisable_params
        if p.get("cred_username") and p.get("cred_password"):
            objstore_credential = cls.get_cred_param(objstore_cred)
            try:
                logger.info(
                    "Creating ObjectStore credential: %s", objstore_cred
                )
                await select_ai.async_create_credential(
                    credential=objstore_credential,
                    replace=True,
                )
                logger.info("ObjectStore credential created.")
            except Exception as exc:
                logger.error(
                    "create_credential() raised %s unexpectedly.", exc
                )
                raise AssertionError(
                    f"create_credential() raised {exc} unexpectedly."
                )
        else:
            logger.info(
                "Skipping ObjectStore credential creation "
                "(CRED_USERNAME/CRED_PASSWORD not set)."
            )

    @classmethod
    async def create_profile(cls, profile_name=None):
        profile_name = profile_name or cls.profile_name
        logger.info("Creating Profile: %s", profile_name)
        p = cls.enabledisable_params
        provider = select_ai.OCIGenAIProvider(
            oci_compartment_id=p["oci_compartment_id"],
            oci_apiformat="GENERIC",
            embedding_model="cohere.embed-english-v3.0",
        )
        profile_attributes = select_ai.ProfileAttributes(
            credential_name=cls.genai_cred,
            provider=provider,
        )
        profile = await select_ai.AsyncProfile(
            profile_name=profile_name,
            attributes=profile_attributes,
            description="OCI GENAI Profile",
            replace=True,
        )
        logger.info("Profile '%s' created successfully.", profile_name)
        return profile

    @classmethod
    async def delete_credential(cls):
        logger.info("Deleting credentials...")
        try:
            await select_ai.async_delete_credential(cls.genai_cred, force=True)
            logger.info("Deleted credential 'GENAI_CRED'")
        except Exception as exc:
            logger.warning("delete_credential() raised %s unexpectedly.", exc)
        try:
            await select_ai.async_delete_credential(
                cls.objstore_cred, force=True
            )
            logger.info("Deleted credential 'OBJSTORE_CRED'")
        except Exception as exc:
            logger.warning("delete_credential() raised %s unexpectedly.", exc)

    @staticmethod
    async def stop_pipeline_if_exists(vector_index):
        try:
            pipeline_name = (await vector_index.get_attributes()).pipeline_name
        except Exception as exc:
            logger.info("Skipping pipeline stop before delete: %s", exc)
            return
        if not pipeline_name:
            return
        try:
            async with select_ai.async_cursor() as cursor:
                await cursor.execute(
                    "BEGIN dbms_cloud_pipeline.stop_pipeline(pipeline_name => :1); END;",
                    [pipeline_name],
                )
        except oracledb.DatabaseError as exc:
            if "ORA-20044" in str(exc):
                logger.info(
                    "Pipeline %s already absent before delete.", pipeline_name
                )
                return
            raise

    @classmethod
    async def delete_index_with_retry(
        cls,
        vector_index,
        include_data=True,
        force=True,
        retries=3,
        delay=2,
    ):
        await cls.stop_pipeline_if_exists(vector_index)
        for attempt in range(retries):
            try:
                await vector_index.delete(
                    include_data=include_data,
                    force=force,
                )
                return
            except oracledb.DatabaseError as exc:
                if "ORA-00054" not in str(exc) or attempt == retries - 1:
                    raise
                logger.info(
                    "Vector index delete hit ORA-00054, retrying (attempt %s/%s)...",
                    attempt + 2,
                    retries,
                )
                await asyncio.sleep(delay)

    async def wait_for_status_table(self, status_table, timeout=60, delay=2):
        """Wait until the asynchronously-created pipeline status table exists."""
        deadline = time.monotonic() + timeout
        attempts = 0
        while True:
            attempts += 1
            try:
                async with select_ai.async_cursor() as cursor:
                    await cursor.execute(
                        f"SELECT COUNT(*) FROM {status_table}"
                    )
                    return await cursor.fetchone()
            except oracledb.DatabaseError as exc:
                if "ORA-00942" not in str(exc):
                    raise
                if time.monotonic() >= deadline:
                    logger.info(
                        "Status table %s was not visible after %s attempts "
                        "within %s seconds.",
                        status_table,
                        attempts,
                        timeout,
                    )
                    return None
                await asyncio.sleep(delay)

    async def wait_for_pipeline_entry(
        self, pipeline_name, timeout=60, delay=2
    ):
        """Wait for ENABLE_VECTOR_INDEX to publish pipeline metadata."""
        deadline = time.monotonic() + timeout
        attempts = 0
        while True:
            attempts += 1
            async with select_ai.async_cursor() as cursor:
                await cursor.execute(
                    "SELECT status_table FROM user_cloud_pipelines "
                    "WHERE pipeline_name = :1",
                    [pipeline_name],
                )
                row = await cursor.fetchone()
            if row and row[0]:
                return row[0]
            if time.monotonic() >= deadline:
                logger.info(
                    "Pipeline %s was not visible after %s attempts within "
                    "%s seconds.",
                    pipeline_name,
                    attempts,
                    timeout,
                )
                return None
            await asyncio.sleep(delay)

    async def test_5501(self):
        """Disabling and enabling the vector index."""
        logger.info("Disabling vector index: %s", self.index_name)
        await self.async_vector_index.disable()
        logger.info("Enabling vector index: %s", self.index_name)
        await self.async_vector_index.enable()
        logger.info("Vector index enabled successfully")

    async def test_5502(self):
        """Disable same vector index twice (should be harmless)."""
        logger.info("First disable of vector index: %s", self.index_name)
        await self.async_vector_index.disable()
        logger.info(
            "Attempting second disable of vector index: %s",
            self.index_name,
        )
        await self.async_vector_index.disable()

    async def test_5503(self):
        """Enable same vector index twice (should be harmless)."""
        logger.info("Enabling vector index: %s", self.index_name)
        await self.async_vector_index.enable()
        await self.async_vector_index.enable()

    async def test_5504(self):
        """Ensure queries work after enabling the vector index."""
        logger.info("Querying test_items table after enabling vector index")
        async with select_ai.async_cursor() as cursor:
            await cursor.execute("select count(*) from test_items")
            (row_count,) = await cursor.fetchone()
            logger.info("Number of rows in test_items: %s", row_count)
        assert row_count == 2
        df = await self.profile.run_sql(prompt="How many rows in test_items")
        logger.info("run_sql returned: %s", df)
        assert df is not None, "run_sql should return a DataFrame object"

    async def test_5505(self):
        """Ensure queries fail after disabling the vector index."""
        logger.info(
            "Disabling vector index: %s to test query blocking",
            self.index_name,
        )
        await self.async_vector_index.disable()
        logger.info("Running query should raise DatabaseError")
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.profile.run_sql(prompt="Show all rows from test_items")
        logger.info(
            "Expected database error confirmed: %s",
            exc_info.value,
        )

    async def test_5506(self):
        """Disabling a nonexistent index raises error."""
        logger.info("Disabling nonexistent index to test error handling")
        invalid_index = AsyncVectorIndex(index_name="does_not_exist")
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await invalid_index.disable()
        logger.info(
            "Expected database error confirmed: %s",
            exc_info.value,
        )

    async def test_5507(self):
        """Enabling a nonexistent index raises error."""
        logger.info("Enabling nonexistent index to test error handling")
        invalid_index = AsyncVectorIndex(index_name="does_not_exist")
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await invalid_index.enable()
        logger.info(
            "Expected database error confirmed: %s",
            exc_info.value,
        )

    async def test_5508(self):
        """Disabling after delete raises error; vector index recreated."""
        logger.info("Deleting vector index: %s", self.index_name)
        await self.delete_index_with_retry(
            self.async_vector_index,
            force=True,
        )
        logger.info("Attempting to disable deleted index")
        with pytest.raises(oracledb.DatabaseError):
            await self.async_vector_index.disable()
        logger.info("Recreating vector index for subsequent tests")
        vector_index = AsyncVectorIndex(
            index_name=self.index_name,
            attributes=self.vector_index_attributes,
            description="Test vector index",
            profile=self.profile,
        )
        await vector_index.create(replace=True)
        logger.info("Vector index recreated successfully")
        self.async_vector_index = await AsyncVectorIndex.fetch(self.index_name)

    async def test_5509(self):
        """Pipeline inactive after disabling the vector index."""
        logger.info(
            "Disabling vector index: %s to check pipeline inactivity",
            self.index_name,
        )
        await self.async_vector_index.disable()
        pipeline_name = f"{self.index_name.upper()}$VECPIPELINE"
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                "SELECT status_table FROM user_cloud_pipelines "
                "WHERE pipeline_name = :1",
                [pipeline_name],
            )
            row = await cursor.fetchone()
            if row is None:
                logger.info(
                    "Pipeline is inactive (no entry in user_cloud_pipelines)"
                )
                assert True
                return
            status_table = row[0]
            logger.info(
                "Status table found: %s, querying should fail",
                status_table,
            )
            with pytest.raises(oracledb.DatabaseError):
                await cursor.execute(
                    f"SELECT * FROM {status_table} FETCH FIRST 1 ROWS ONLY"
                )

    async def test_5510(self):
        """Pipeline metadata is available after enabling the vector index."""
        logger.info(
            "Disabling then enabling vector index: %s", self.index_name
        )
        await self.async_vector_index.disable()
        await self.async_vector_index.enable()
        pipeline_name = f"{self.index_name.upper()}$VECPIPELINE"
        logger.info("Checking pipeline activity after enabling vector index")
        status_table = await self.wait_for_pipeline_entry(pipeline_name)
        assert (
            status_table is not None
        ), f"No pipeline entry found for {pipeline_name}"
        logger.info("Status table found: %s", status_table)
        if status_table is not None:
            count_row = await self.wait_for_status_table(status_table)
            assert (
                count_row is not None
            ), f"No result returned from status_table {status_table}"
            assert (
                count_row[0] >= 0
            ), "Pipeline table should be accessible when enabled"
        logger.info("Pipeline metadata is available after enable.")

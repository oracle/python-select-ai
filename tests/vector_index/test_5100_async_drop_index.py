# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import asyncio
import logging

import oracledb
import pytest
import select_ai
from select_ai import OracleVectorIndexAttributes

logger = logging.getLogger("TestAsyncDeleteVectorIndex")

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="class")
def delete_vec_params(request, vcidx_params):
    request.cls.delete_vec_params = vcidx_params


@pytest.fixture(scope="class", autouse=True)
async def setup_and_teardown(request, async_connect, delete_vec_params):
    logger.info("=== Setting up TestAsyncDeleteVectorIndex class ===")
    assert await select_ai.async_is_connected(), "Connection to DB failed"
    logger.info("Fetching credential secrets and OCI configuration...")
    await request.cls.create_credential()
    request.cls.profile = await request.cls.create_profile()
    logger.info("Setup complete.")
    yield
    logger.info("=== Tearing down TestAsyncDeleteVectorIndex class ===")
    await request.cls.delete_profile(request.cls.profile)
    await request.cls.delete_credential()
    logger.info("Teardown complete.\n")


@pytest.fixture(autouse=True)
async def vector_index_test_state(request):
    logger.info("SetUp for %s", request.function.__name__)
    request.cls.objstore_cred = "OBJSTORE_CRED"
    request.cls.vecidx = select_ai.AsyncVectorIndex()
    params = request.cls.delete_vec_params
    request.cls.vector_index_attributes = OracleVectorIndexAttributes(
        location=params["embedding_location"],
        object_storage_credential_name=request.cls.objstore_cred,
    )

    await request.cls.delete_and_wait()

    request.cls.index_name = "test_vector_index"
    request.cls.async_vector_index = select_ai.AsyncVectorIndex(
        index_name=request.cls.index_name,
        attributes=request.cls.vector_index_attributes,
        description="Test vector index",
        profile=request.cls.profile,
    )
    await request.cls.async_vector_index.create(replace=True)
    logger.info(
        "Vector index '%s' created for test.", request.cls.index_name
    )
    yield
    logger.info("TearDown for %s", request.function.__name__)
    try:
        await request.cls.async_vector_index.delete(force=True)
        logger.info(
            "Vector index '%s' deleted successfully.", request.cls.index_name
        )
    except Exception as exc:
        logger.warning("Warning: vector index cleanup failed: %s", exc)


@pytest.mark.usefixtures("delete_vec_params", "setup_and_teardown")
class TestAsyncDeleteVectorIndex:
    @classmethod
    def get_native_cred_param(cls, cred_name=None) -> dict:
        logger.info("Preparing native credential params for: %s", cred_name)
        params = cls.delete_vec_params
        return dict(
            credential_name=cred_name,
            user_ocid=params["user_ocid"],
            tenancy_ocid=params["tenancy_ocid"],
            private_key=params["private_key"],
            fingerprint=params["fingerprint"],
        )

    @classmethod
    def get_cred_param(cls, cred_name=None) -> dict:
        logger.info("Preparing basic credential params for: %s", cred_name)
        params = cls.delete_vec_params
        return dict(
            credential_name=cred_name,
            username=params["cred_username"],
            password=params["cred_password"],
        )

    @classmethod
    async def create_credential(
        cls, genai_cred="GENAI_CRED", objstore_cred="OBJSTORE_CRED"
    ):
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
            logger.error(
                "create_credential() raised %s unexpectedly.", exc
            )
            raise AssertionError(
                f"create_credential() raised {exc} unexpectedly."
            )

        params = cls.delete_vec_params
        if params.get("cred_username") and params.get("cred_password"):
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
    async def create_profile(cls, profile_name="vector_ai_profile"):
        logger.info("Creating Profile: %s", profile_name)
        params = cls.delete_vec_params
        provider = select_ai.OCIGenAIProvider(
            oci_compartment_id=params["oci_compartment_id"],
            oci_apiformat="GENERIC",
            embedding_model="cohere.embed-english-v3.0",
        )
        profile_attributes = select_ai.ProfileAttributes(
            credential_name="GENAI_CRED",
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
    async def delete_profile(cls, profile):
        logger.info("Deleting profile...")
        try:
            await profile.delete()
            logger.info(
                "Profile '%s' deleted successfully.", profile.profile_name
            )
        except Exception as exc:
            logger.error("profile.delete() raised %s unexpectedly.", exc)
            raise AssertionError(
                f"profile.delete() raised {exc} unexpectedly."
            )

    @classmethod
    async def delete_credential(cls):
        logger.info("Deleting credentials...")
        try:
            await select_ai.async_delete_credential("GENAI_CRED", force=True)
            logger.info("Deleted credential 'GENAI_CRED'")
        except Exception as exc:
            logger.warning(
                "delete_credential() raised %s unexpectedly.", exc
            )
        try:
            await select_ai.async_delete_credential("OBJSTORE_CRED", force=True)
            logger.info("Deleted credential 'OBJSTORE_CRED'")
        except Exception as exc:
            logger.warning(
                "delete_credential() raised %s unexpectedly.", exc
            )

    @classmethod
    async def delete_and_wait(cls, force=True, pattern=".*", wait_seconds=1):
        logger.info("Deleting indexes matching pattern.")
        all_indexes = [
            index async for index in cls.vecidx.list(index_name_pattern=pattern)
        ]
        if not all_indexes:
            logger.info("No indexes found to delete.")
            return
        for index in all_indexes:
            try:
                await index.delete(force=force)
                logger.info("Deleted index: %s", index.index_name)
                await asyncio.sleep(wait_seconds)
            except Exception as exc:
                logger.warning(
                    "Warning: failed to delete index %s: %s",
                    index.index_name,
                    exc,
                )
        remaining = [
            index async for index in cls.vecidx.list(index_name_pattern=pattern)
        ]
        logger.info(
            "Remaining indexes after delete: %s",
            [index.index_name for index in remaining],
        )

    async def assert_index_count(self, pattern, expected):
        actual = [
            index async for index in self.vecidx.list(index_name_pattern=pattern)
        ]
        logger.info(
            "Indexes matching '%s': %s",
            pattern,
            [index.index_name for index in actual],
        )
        assert len(actual) == expected, (
            f"Expected {expected} indexes, got {len(actual)}"
        )

    async def verify_and_cleanup_vectab(self, vector_index_name: str):
        table_name = f"{vector_index_name}$vectab".upper()
        logger.info("Verifying and cleaning up vector table: %s", table_name)
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                """
                SELECT column_name
                FROM user_tab_columns
                WHERE table_name = :table_name
                ORDER BY column_id
                """,
                {"table_name": table_name},
            )
            cols = [row[0] for row in await cursor.fetchall()]
            logger.info("Columns found in %s: %s", table_name, cols)
            expected_cols = ["CONTENT", "ATTRIBUTES", "EMBEDDING"]
            assert cols == expected_cols, (
                f"Unexpected columns for {table_name}: {cols}"
            )
            await cursor.execute(f"DROP TABLE {table_name} PURGE")
            logger.info("Table %s dropped successfully.", table_name)

    async def test_5101(self):
        """Test single vector index deletion removes the index."""
        logger.info("Deleting vector index (single delete)")
        await self.assert_index_count("^test_vector_index", 1)
        await self.async_vector_index.delete(force=True)
        logger.info("Delete called on vector index.")
        await asyncio.sleep(1)
        await self.assert_index_count("^test_vector_index", 0)
        logger.info("Single-delete verified: index removed")

    async def test_5103(self):
        """Test deleting the same vector index twice."""
        logger.info("Deleting vector index first time")
        await self.async_vector_index.delete(force=True)
        logger.info("Deleting vector index second time (no-op expected)")
        await asyncio.sleep(1)
        await self.async_vector_index.delete(force=True)
        await asyncio.sleep(1)
        await self.assert_index_count("^test_vector_index", 0)
        logger.info("Double-delete verified: index removed")

    async def test_5104(self):
        """Test delete with include_data=True also removes table."""
        logger.info("Deleting index with include_data=True (metadata + table)")
        await self.async_vector_index.delete(include_data=True, force=True)
        await asyncio.sleep(1)
        await self.assert_index_count("^test_vector_index", 0)
        table_name = "TEST_VECTOR_INDEX$VECTAB"
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                """
                SELECT COUNT(*)
                FROM user_tables
                WHERE table_name = :table_name
                """,
                {"table_name": table_name},
            )
            (count,) = await cursor.fetchone()
        logger.info(
            "Verified vector table '%s' removed: %s", table_name, count == 0
        )
        assert count == 0

    async def test_5105(self):
        """Test delete with include_data=False doesn't remove table."""
        logger.info("Deleting index with include_data=False (metadata only)")
        await self.async_vector_index.delete(include_data=False, force=True)
        await asyncio.sleep(1)
        await self.assert_index_count("^test_vector_index", 0)
        logger.info(
            "Attempting to recreate index (should fail due to leftover table)"
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.create(replace=True)
        logger.info("Expected DatabaseError on recreate: %s", exc_info.value)
        assert "ORA-00955" in str(exc_info.value)
        await self.verify_and_cleanup_vectab("test_vector_index")
        logger.info("Vector table cleaned up after failed recreate")

    async def test_5106(self):
        """Test delete twice with include_data=False then cleanup."""
        logger.info("Deleting index metadata only first time")
        await self.async_vector_index.delete(include_data=False, force=True)
        await asyncio.sleep(1)
        await self.assert_index_count("^test_vector_index", 0)
        logger.info("Attempting to recreate index (should fail)")
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.create(replace=True)
        assert "ORA-00955" in str(exc_info.value)
        await self.verify_and_cleanup_vectab("test_vector_index")
        logger.info("Vector table cleaned up")
        logger.info("Deleting index metadata only second time (no-op)")
        await self.async_vector_index.delete(include_data=False, force=True)
        await self.assert_index_count("^test_vector_index", 0)

    async def test_5107(self):
        """Test delete twice with include_data=False and cleanup after failed recreate."""
        logger.info("Deleting metadata only first time")
        await self.async_vector_index.delete(include_data=False, force=True)
        await asyncio.sleep(1)
        await self.assert_index_count("^test_vector_index", 0)
        logger.info("Attempting recreate (expected failure)")
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.create(replace=True)
        logger.info("Recreate failed (expected): %s", exc_info.value)
        assert "ORA-00955" in str(exc_info.value)
        logger.info("Deleting metadata second time (no-op)")
        await self.async_vector_index.delete(include_data=False, force=True)
        await self.verify_and_cleanup_vectab("test_vector_index")
        await self.assert_index_count("^test_vector_index", 0)
        logger.info("Cleanup complete")

    async def test_5108(self):
        """Test delete and then recreate a vector index."""
        logger.info("Deleting index before recreation")
        await self.async_vector_index.delete(force=True)
        await asyncio.sleep(1)
        logger.info("Recreating vector index")
        await self.async_vector_index.create(replace=True)
        await asyncio.sleep(1)
        await self.assert_index_count("^test_vector_index", 1)
        logger.info("Recreate verified: index exists")

    async def test_5109(self):
        """Test delete of a nonexistent index (should not error)."""
        idx = select_ai.AsyncVectorIndex(
            index_name="nonexistent_index",
            attributes=self.vector_index_attributes,
            profile=self.profile,
        )
        logger.info("Attempting to delete nonexistent index")
        await idx.delete(force=True)
        await asyncio.sleep(1)
        await self.assert_index_count("^nonexistent_index", 0)
        logger.info("Nonexistent delete verified (no error)")

    async def test_5110(self):
        """Test delete after set_attribute was called."""
        logger.info("Setting temporary attributes before delete")
        await self.async_vector_index.create(replace=True)
        try:
            await self.async_vector_index.set_attribute(
                attribute_name="match_limit",
                attribute_value=10,
            )
        except Exception as exc:
            logger.error("set_attribute() raised %s unexpectedly.", exc)
            pytest.fail(f"set_attribute() raised {exc} unexpectedly.")
        logger.info("Deleting index after setting attributes")
        await self.async_vector_index.delete(force=True)
        await asyncio.sleep(1)
        actual_indexes = [
            index
            async for index in self.async_vector_index.list(
                index_name_pattern="^test_vector_index$"
            )
        ]
        logger.info("Indexes remaining after delete: %s", actual_indexes)
        assert len(actual_indexes) == 0
        logger.info("Delete after attributes verified")

    async def test_5111(self):
        """Test case-sensitive name for create and delete."""
        idx = select_ai.AsyncVectorIndex(
            index_name="CaseSensitiveIndex",
            attributes=self.vector_index_attributes,
            profile=self.profile,
        )
        logger.info("Creating case-sensitive index")
        await idx.create(replace=True)
        logger.info("Deleting case-sensitive index")
        await idx.delete(force=True)
        await asyncio.sleep(1)
        await self.assert_index_count("^CaseSensitiveIndex", 0)
        logger.info("Case-sensitive index delete verified")

    async def test_5112(self):
        """Test creation and deletion with long index name."""
        long_name = "index_" + "x" * 40
        idx = select_ai.AsyncVectorIndex(
            index_name=long_name,
            attributes=self.vector_index_attributes,
            profile=self.profile,
        )
        logger.info("Creating long-name index: %s", long_name)
        await idx.create(replace=True)
        logger.info("Deleting long-name index: %s", long_name)
        await idx.delete(force=True)
        await asyncio.sleep(1)
        await self.assert_index_count(f"^{long_name}$", 0)
        logger.info("Long-name index delete verified")

    async def test_5113(self):
        """Test creation and bulk deletion of indexes."""
        names = [f"bulk_idx_{i}" for i in range(3)]
        logger.info("Creating bulk indexes")
        for name in names:
            await select_ai.AsyncVectorIndex(
                index_name=name,
                attributes=self.vector_index_attributes,
                profile=self.profile,
            ).create(replace=True)
            logger.info("Created %s", name)
        logger.info("Deleting bulk indexes")
        for name in names:
            await select_ai.AsyncVectorIndex(
                index_name=name,
                attributes=self.vector_index_attributes,
                profile=self.profile,
            ).delete(force=True)
            await asyncio.sleep(1)
            logger.info("Deleted %s", name)
        await self.assert_index_count("^bulk_idx_", 0)
        logger.info("Bulk delete verified")

    async def test_5114(self):
        """Test that list returns empty after index is deleted."""
        logger.info("Deleting index and verifying list is empty")
        await self.async_vector_index.delete(force=True)
        await asyncio.sleep(1)
        actual_indexes = [
            index
            async for index in self.async_vector_index.list(
                index_name_pattern=".*"
            )
        ]
        index_names = [index.index_name for index in actual_indexes]
        logger.info("Actual indexes after delete: %s", index_names)
        actual = [
            index
            async for index in self.async_vector_index.list(
                index_name_pattern="^test_vector_index"
            )
        ]
        assert actual == []
        logger.info("List verification successful: no remaining indexes")

    async def test_5115(self):
        """Test delete then recreate index with same name."""
        logger.info("Deleting index before recreate with same name")
        await self.async_vector_index.delete(force=True)
        await asyncio.sleep(1)
        logger.info("Recreating index with same name")
        await self.async_vector_index.create(replace=False)
        await asyncio.sleep(1)
        await self.assert_index_count("^test_vector_index", 1)
        logger.info("Recreate same-name index verified")

    async def test_5116(self):
        """Test delete of one out of multiple indexes."""
        idx1 = select_ai.AsyncVectorIndex(
            index_name="IDX_1",
            attributes=self.vector_index_attributes,
            profile=self.profile,
        )
        idx2 = select_ai.AsyncVectorIndex(
            index_name="IDX_2",
            attributes=self.vector_index_attributes,
            profile=self.profile,
        )
        logger.info("Creating two indexes IDX_1 and IDX_2")
        await idx1.create(replace=True)
        await idx2.create(replace=True)
        logger.info("Deleting IDX_1 only")
        await self.delete_and_wait(force=True, pattern="^IDX_1$")
        remaining_idx2 = [
            index
            async for index in self.async_vector_index.list(
                index_name_pattern="^IDX_2$"
            )
        ]
        logger.info(
            "IDX_2 entries after IDX_1 delete: %s", remaining_idx2
        )
        assert len(remaining_idx2) == 1
        logger.info("IDX_2 remains after IDX_1 delete")

    async def test_5117(self):
        """Test deletion by pattern."""
        logger.info("Deleting index with pattern '^test_vector_index$'")
        await self.async_vector_index.create(replace=True)
        await self.async_vector_index.delete(force=True)
        await asyncio.sleep(1)
        actual = [
            index
            async for index in self.async_vector_index.list(
                index_name_pattern="^test_vector_index$"
            )
        ]
        logger.info("List entries after pattern delete: %s", actual)
        assert len(actual) == 0
        logger.info("Pattern delete verified")

    async def test_5118(self):
        """Test delete with force=True option."""
        logger.info("Deleting index with force=True")
        await self.async_vector_index.create(replace=True)
        await self.async_vector_index.delete(force=True)
        await asyncio.sleep(1)
        await self.assert_index_count("^test_vector_index$", 0)
        logger.info("Force delete verified")

    async def test_5119(self):
        """Test delete with force=False option."""
        logger.info("Creating index before delete (force=False)")
        await self.async_vector_index.create(replace=True)
        logger.info("Deleting index with force=False")
        await self.async_vector_index.delete(force=False)
        await asyncio.sleep(1)
        await self.assert_index_count("^test_vector_index$", 0)
        logger.info("Delete verified successfully with force=False")

    async def test_5120(self):
        """Test delete with force=False called twice in a row."""
        logger.info("Deleting index first time (force=False)")
        await self.async_vector_index.delete(force=False)
        await asyncio.sleep(1)
        await self.assert_index_count("^test_vector_index$", 0)
        logger.info("First delete succeeded")
        logger.info("Attempting second delete (expected to fail)")
        with pytest.raises(Exception) as exc_info:
            await self.async_vector_index.delete(force=False)
        assert "does not exist" in str(exc_info.value)
        logger.info("Expected failure confirmed: %s", exc_info.value)
        await self.assert_index_count("^test_vector_index$", 0)
        logger.info("Index still absent after failed second delete")

    async def test_5121(self):
        """Test delete include_data=False and force=False (leftover vectab)."""
        logger.info("Deleting index with include_data=False and force=False")
        await self.async_vector_index.delete(
            include_data=False,
            force=False,
        )
        await asyncio.sleep(1)
        await self.assert_index_count("^test_vector_index", 0)
        logger.info(
            "Attempting to recreate index (expected to fail - leftover data)"
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.create(replace=False)
        assert "ORA-00955" in str(exc_info.value)
        logger.info(
            "Expected recreate failure confirmed: %s", exc_info.value
        )
        logger.info("Cleaning up leftover vector table")
        await self.verify_and_cleanup_vectab("test_vector_index")
        logger.info(
            "Cleanup complete after include_data=False, force=False delete"
        )

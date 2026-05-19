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
from select_ai import OracleVectorIndexAttributes

logger = logging.getLogger("TestAsyncCreateVectorIndex")

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="class")
def vector_index_params(request, vcidx_params):
    request.cls.vector_index_params = vcidx_params


@pytest.fixture(scope="class", autouse=True)
async def setup_and_teardown(request, async_connect, vector_index_params):
    """
    The shared async connection fixture from tests/conftest.py owns lifecycle.
    """
    logger.info("\n=== Setting up TestAsyncCreateVectorIndex class ===")
    assert await select_ai.async_is_connected(), "Connection to DB failed"
    logger.info("Fetching credential secrets and OCI configuration...")
    await request.cls.create_credential()
    request.cls.profile = await request.cls.create_profile()
    logger.info("Setup complete.\n")
    yield
    logger.info("\n=== Tearing down TestAsyncCreateVectorIndex class ===")
    await request.cls.delete_profile(request.cls.profile)
    await request.cls.delete_credential()
    logger.info("Teardown complete.\n")


@pytest.fixture(autouse=True)
async def vector_index_test_state(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    request.cls.objstore_cred = "OBJSTORE_CRED"
    params = request.cls.vector_index_params
    request.cls.vector_index_attributes = OracleVectorIndexAttributes(
        location=params["embedding_location"],
        object_storage_credential_name=request.cls.objstore_cred,
    )
    request.cls.async_vector_index = select_ai.AsyncVectorIndex(
        index_name="test_vector_index",
        attributes=request.cls.vector_index_attributes,
        description="Test vector index",
        profile=request.cls.profile,
    )
    yield
    try:
        await select_ai.AsyncVectorIndex(
            index_name="test_vector_index"
        ).delete(force=True)
        logger.info("Vector index deleted successfully.")
    except Exception as exc:
        logger.warning("Warning: vector index cleanup failed: %s", exc)
    logger.info("--- Finished test: %s ---", request.function.__name__)


@pytest.mark.usefixtures("vector_index_params", "setup_and_teardown")
class TestAsyncCreateVectorIndex:
    @classmethod
    def get_native_cred_param(cls, cred_name=None) -> dict:
        logger.info("Preparing native credential params for: %s", cred_name)
        params = cls.vector_index_params
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
        params = cls.vector_index_params
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
            raise AssertionError(
                f"create_credential() raised {exc} unexpectedly."
            )

        params = cls.vector_index_params
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
        params = cls.vector_index_params
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

    async def test_5001(self):
        """Test successful vector index creation."""
        try:
            await self.async_vector_index.create(replace=True)
            logger.info("Vector index created successfully.")
        except Exception as exc:
            pytest.fail(
                f"VectorIndex.create raised an unexpected exception: {exc}"
            )
        logger.info("Verifying created vector index...")
        vector_index = select_ai.AsyncVectorIndex()
        indexes = [index.index_name async for index in vector_index.list()]
        logger.info("Indexes found: %s", indexes)
        assert "TEST_VECTOR_INDEX" in indexes
        logger.info("Verified vector index creation successfully.")

    async def test_5002(self):
        """Test vector index creation with replace=False."""
        try:
            await self.async_vector_index.create(replace=False)
            logger.info("Vector index created successfully.")
        except Exception as exc:
            pytest.fail(
                f"VectorIndex.create raised an unexpected exception: {exc}"
            )
        logger.info("Verifying created vector index...")
        vector_index = select_ai.AsyncVectorIndex()
        indexes = [index.index_name async for index in vector_index.list()]
        logger.info("Indexes found: %s", indexes)
        assert "TEST_VECTOR_INDEX" in indexes
        logger.info("Verified vector index presence.")

    async def test_5003(self):
        """Test vector index creation with empty description."""
        vector_index = select_ai.AsyncVectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            description="",
            profile=self.profile,
        )
        try:
            await vector_index.create(replace=True)
            logger.info(
                "Vector index created successfully with empty description."
            )
        except Exception as exc:
            pytest.fail(
                f"VectorIndex.create raised an unexpected exception: {exc}"
            )
        logger.info("Verifying created vector index...")
        index_list = select_ai.AsyncVectorIndex()
        indexes = [index.index_name async for index in index_list.list()]
        logger.info("Indexes found: %s", indexes)
        assert "TEST_VECTOR_INDEX" in indexes
        logger.info(
            "Verified vector index creation with empty description."
        )

    async def test_5004(self):
        """Test vector index recreation with replace=True."""
        try:
            await self.async_vector_index.create(replace=True)
            logger.info("First creation successful.")
            await self.async_vector_index.create(replace=True)
            logger.info("Second creation successful with replace=True.")
        except Exception as exc:
            pytest.fail(
                f"VectorIndex.create raised an unexpected exception: {exc}"
            )

    async def test_5005(self):
        """Test vector index recreation with replace=False (expect failure)."""
        try:
            await self.async_vector_index.create(replace=False)
            logger.info("First creation successful.")
        except Exception as exc:
            pytest.fail(
                f"Create vector index failed unexpectedly: {exc}"
            )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.create(replace=False)
        logger.info("Expected DatabaseError raised: %s", exc_info.value)
        assert "ORA-20048" in str(exc_info.value)
        assert "already exists" in str(exc_info.value)
        logger.info("Verified error on duplicate creation with replace=False.")

    async def test_5006(self):
        """Test minimal attribute vector index creation."""
        vector_index = select_ai.AsyncVectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            profile=self.profile,
        )
        try:
            await vector_index.create(replace=True)
            logger.info(
                "Vector index created successfully with minimal attributes."
            )
        except Exception as exc:
            pytest.fail(
                f"VectorIndex.create raised an unexpected exception: {exc}"
            )

    async def test_5007(self):
        """Test vector index recreation after delete."""
        try:
            await self.async_vector_index.create(replace=True)
            logger.info("Vector index created successfully.")
        except Exception as exc:
            pytest.fail(
                f"VectorIndex.create raised an unexpected exception: {exc}"
            )
        logger.info("Deleting vector index...")
        await select_ai.AsyncVectorIndex(
            index_name="test_vector_index"
        ).delete(force=True)
        logger.info("Vector index deleted successfully.")
        logger.info("Recreating vector index...")
        try:
            await self.async_vector_index.create(replace=True)
            logger.info("Vector index recreated successfully.")
        except Exception as exc:
            pytest.fail(
                f"VectorIndex.create raised an unexpected exception: {exc}"
            )

    async def test_5008(self):
        """Test vector index creation with invalid credential."""
        params = self.vector_index_params
        vector_index_attributes = OracleVectorIndexAttributes(
            location=params["embedding_location"],
            object_storage_credential_name="invalidObjStore_cred",
        )
        vector_index = select_ai.AsyncVectorIndex(
            index_name="test_vector_index",
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.profile,
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await vector_index.create(replace=True)
        logger.info("Expected DatabaseError raised: %s", exc_info.value)

    async def test_5009(self):
        """Test vector index creation with invalid location."""
        vector_index_attributes = OracleVectorIndexAttributes(
            location="invalid_location",
            object_storage_credential_name=self.objstore_cred,
        )
        vector_index = select_ai.AsyncVectorIndex(
            index_name="test_vector_index",
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.profile,
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await vector_index.create(replace=True)
        logger.info("Expected DatabaseError raised: %s", exc_info.value)

    async def test_5010(self):
        """Test vector index creation with missing attributes."""
        with pytest.raises(AttributeError):
            await select_ai.AsyncVectorIndex(
                index_name="test_vector_index",
                attributes=None,
                profile=self.profile,
            ).create()
        logger.info("Expected AttributeError raised for missing attributes.")

    async def test_5011(self):
        """Test vector index creation with invalid attributes type."""
        with pytest.raises(TypeError):
            await select_ai.AsyncVectorIndex(
                index_name="test_vector_index",
                attributes="invalid_attributes",
                profile=self.profile,
            ).create()
        logger.info("Expected TypeError raised for invalid attribute type.")

    async def test_5012(self):
        """Test vector index creation with invalid name type."""
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.AsyncVectorIndex(
                index_name=12345,
                attributes=self.vector_index_attributes,
                profile=self.profile,
            ).create()
        assert "ORA-20048" in str(exc_info.value)
        assert "Invalid vector index name" in str(exc_info.value)
        logger.info("Expected DatabaseError raised: %s", exc_info.value)

    async def test_5013(self):
        """Test vector index creation with empty name."""
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await select_ai.AsyncVectorIndex(
                index_name="",
                attributes=self.vector_index_attributes,
                profile=self.profile,
            ).create()
        assert "ORA-20048" in str(exc_info.value)
        assert "Missing vector index name" in str(exc_info.value)
        logger.info("Expected DatabaseError raised: %s", exc_info.value)

    async def test_5014(self):
        """Test vector index creation with invalid profile."""
        with pytest.raises(TypeError) as exc_info:
            vector_index = select_ai.AsyncVectorIndex(
                index_name="test_vector_index",
                attributes=self.vector_index_attributes,
                description="Test vector index",
                profile="invalid_profile",
            )
            await vector_index.create()
        logger.info(
            "Expected TypeError raised for invalid profile: %s",
            exc_info.value,
        )

    async def test_5015(self):
        """Test vector index creation with None attributes."""
        with pytest.raises(TypeError) as exc_info:
            vector_index = select_ai.AsyncVectorIndex(
                index_name="test_vector_index",
                attributes=None,
                description="invalid_profile",
                profile="invalid_profile",
            )
            await vector_index.create()
        logger.info(
            "Expected TypeError raised for None attributes: %s",
            exc_info.value,
        )

    async def test_5016(self):
        """Test vector index creation with long name (>128 chars)."""
        long_name = "X" * 150
        vector_index = select_ai.AsyncVectorIndex(
            index_name=long_name,
            attributes=self.vector_index_attributes,
            profile=self.profile,
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await vector_index.create()
        logger.info(
            "Expected DatabaseError raised for long name: %s",
            exc_info.value,
        )

    async def test_5017(self):
        """Test vector index creation with long description."""
        long_desc = "D" * 5000
        vector_index = select_ai.AsyncVectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            description=long_desc,
            profile=self.profile,
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await vector_index.create(replace=True)
        assert "ORA-20045" in str(exc_info.value)
        assert "description is too long" in str(exc_info.value)
        logger.info("Expected DatabaseError raised: %s", exc_info.value)

    async def test_5018(self):
        """Test multiple recreations of vector index (10x)."""
        for _ in range(10):
            await self.async_vector_index.create(replace=True)
        logger.info("Successfully recreated vector index multiple times.")

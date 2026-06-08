# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import logging

import pytest
import select_ai
from select_ai import AsyncVectorIndex, OracleVectorIndexAttributes
from select_ai.errors import VectorIndexNotFoundError

logger = logging.getLogger("TestAsyncGetVectorIndexAttributes")

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="class")
def vector_attr_params(request, vcidx_params):
    request.cls.vector_attr_params = vcidx_params


@pytest.fixture(scope="class", autouse=True)
async def setup_and_teardown(
    request,
    async_connect,
    vector_attr_params,
    test_env,
):
    logger.info("=== Setting up TestAsyncGetVectorIndexAttributes class ===")
    p = request.cls.vector_attr_params

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
    request.cls.reconnect_params = test_env.connect_params()

    logger.info("Fetching credential secrets and OCI configuration...")
    await request.cls.create_credential()
    request.cls.profile = await request.cls.create_profile()
    logger.info("Profile 'vector_ai_profile' created successfully.")

    request.cls.index_name = "test_vector_index_attr"
    vi_attrs = OracleVectorIndexAttributes(
        location=p["embedding_location"],
        object_storage_credential_name="OBJSTORE_CRED",
    )
    request.cls.vector_index_attributes = vi_attrs

    vi = AsyncVectorIndex(
        index_name=request.cls.index_name,
        attributes=vi_attrs,
        description="Test vector index",
        profile=request.cls.profile,
    )
    await vi.create(replace=True)

    created_indexes = [
        idx.index_name async for idx in AsyncVectorIndex.list()
    ]
    assert request.cls.index_name.upper() in created_indexes, (
        f"VectorIndex {request.cls.index_name} was not created"
    )

    yield

    logger.info("=== Tearing down TestAsyncGetVectorIndexAttributes class ===")

    try:
        vector_index = AsyncVectorIndex(index_name=request.cls.index_name)
        await vector_index.delete(force=True)
    except Exception as exc:
        logger.warning("drop vector index failed: %s", exc)

    try:
        await request.cls.profile.delete()
    except Exception as exc:
        logger.warning("profile.delete() raised %s unexpectedly.", exc)

    await request.cls.delete_credential()


@pytest.fixture(autouse=True)
async def vector_index_state(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    request.cls.async_vector_index = await AsyncVectorIndex.fetch(
        request.cls.index_name
    )
    yield
    logger.info("--- Finished test: %s ---", request.function.__name__)


@pytest.mark.usefixtures("vector_attr_params", "setup_and_teardown")
class TestAsyncGetVectorIndexAttributes:
    @classmethod
    def get_native_cred_param(cls, cred_name=None):
        logger.info("Preparing native credential params for: %s", cred_name)
        p = cls.vector_attr_params
        return dict(
            credential_name=cred_name,
            user_ocid=p["user_ocid"],
            tenancy_ocid=p["tenancy_ocid"],
            private_key=p["private_key"],
            fingerprint=p["fingerprint"],
        )

    @classmethod
    def get_cred_param(cls, cred_name=None):
        logger.info("Preparing basic credential params for: %s", cred_name)
        p = cls.vector_attr_params
        return dict(
            credential_name=cred_name,
            username=p["cred_username"],
            password=p["cred_password"],
        )

    @classmethod
    async def create_credential(
        cls,
        genai_cred="GENAI_CRED",
        objstore_cred="OBJSTORE_CRED",
    ):
        logger.info("Creating credentials: %s, %s", genai_cred, objstore_cred)
        genai_credential = cls.get_native_cred_param(genai_cred)
        await select_ai.async_create_credential(
            credential=genai_credential,
            replace=True,
        )

        p = cls.vector_attr_params
        if p.get("cred_username") and p.get("cred_password"):
            objstore_credential = cls.get_cred_param(objstore_cred)
            await select_ai.async_create_credential(
                credential=objstore_credential,
                replace=True,
            )
            logger.info("Credentials created.")
        else:
            logger.info(
                "Skipping ObjectStore credential creation "
                "(CRED_USERNAME/CRED_PASSWORD not set)."
            )

    @classmethod
    async def create_profile(cls, profile_name="vector_ai_profile"):
        p = cls.vector_attr_params
        return await select_ai.AsyncProfile(
            profile_name=profile_name,
            attributes=select_ai.ProfileAttributes(
                credential_name="GENAI_CRED",
                provider=select_ai.OCIGenAIProvider(
                    oci_compartment_id=p["oci_compartment_id"],
                    oci_apiformat="GENERIC",
                    embedding_model="cohere.embed-english-v3.0",
                ),
            ),
            description="OCI GENAI Profile",
            replace=True,
        )

    @classmethod
    async def delete_credential(cls):
        try:
            await select_ai.async_delete_credential("GENAI_CRED", force=True)
            logger.info("Deleted credential 'GENAI_CRED'")
        except Exception as exc:
            logger.warning("delete_credential() raised %s unexpectedly.", exc)
        try:
            await select_ai.async_delete_credential("OBJSTORE_CRED", force=True)
            logger.info("Deleted credential 'OBJSTORE_CRED'")
        except Exception as exc:
            logger.warning("delete_credential() raised %s unexpectedly.", exc)

    async def test_5301(self):
        """Get vector index attributes and verify type."""
        logger.info("Getting vector index attributes and verifying type...")
        attrs = await self.async_vector_index.get_attributes()
        assert isinstance(attrs, OracleVectorIndexAttributes)
        logger.info("Attributes type verified successfully.")

    async def test_5302(self):
        """Verify core values of vector index attributes."""
        logger.info("Getting vector index attributes and verifying core values...")
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.location == self.embedding_location
        assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
        assert attrs.profile_name == "vector_ai_profile"
        assert attrs.pipeline_name == f"{self.index_name.upper()}$VECPIPELINE"
        logger.info("Core attribute values verified successfully.")

    async def test_5303(self):
        """Additional sanity checks on vector index attributes."""
        logger.info(
            "Performing additional sanity checks on vector index attributes..."
        )
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.chunk_size is None
        assert attrs.chunk_overlap is None
        assert attrs.match_limit is None
        assert attrs.refresh_rate == 1440
        assert attrs.vector_distance_metric is None
        assert attrs.vector_db_provider.value == "oracle"
        logger.info("Additional sanity checks passed successfully.")

    async def test_5304(self):
        """Verify required fields in attributes object."""
        logger.info("Verifying attributes object contains required fields...")
        attrs = await self.async_vector_index.get_attributes()
        logger.info("Attributes dict: %s", attrs.__dict__)
        assert hasattr(attrs, "location")
        assert hasattr(attrs, "object_storage_credential_name")
        logger.info("Attributes contain all expected fields.")

    async def test_5305(self):
        """Repeatability: fetch attributes twice and compare."""
        logger.info("Fetching attributes twice to confirm repeatability...")
        attrs1 = await self.async_vector_index.get_attributes()
        attrs2 = await self.async_vector_index.get_attributes()
        assert attrs1.location == attrs2.location
        logger.info("Attribute values are repeatable across calls.")

    async def test_5306(self):
        """Test case-insensitive index name handling."""
        logger.info("Testing case-insensitive index name handling...")
        vector_index = await AsyncVectorIndex.fetch(self.index_name.lower())
        attrs = await vector_index.get_attributes()
        assert attrs.location == self.embedding_location
        logger.info("Case-insensitive index name test passed.")

    async def test_5307(self):
        """Type check on key vector index attributes."""
        logger.info("Performing type check on key vector index attributes...")
        attrs = await self.async_vector_index.get_attributes()
        logger.info("%s", attrs)
        assert isinstance(attrs.location, str)
        assert isinstance(attrs.profile_name, str)
        assert isinstance(attrs.object_storage_credential_name, str)
        logger.info("All attribute fields are of correct type.")

    async def test_5308(self):
        """Calling get_attributes on nonexistent index raises error."""
        logger.info("Testing get_attributes() with a nonexistent index...")
        with pytest.raises(VectorIndexNotFoundError):
            await AsyncVectorIndex(index_name="does_not_exist").get_attributes()
        logger.info(
            "Nonexistent index correctly raised VectorIndexNotFoundError."
        )

    async def test_5309(self):
        """Verify error after deleting a temporary vector index."""
        logger.info("Testing error after deleting a temporary vector index...")
        temp_index = AsyncVectorIndex(
            index_name="temp_index_for_delete",
            attributes=OracleVectorIndexAttributes(
                location=self.embedding_location,
                object_storage_credential_name="OBJSTORE_CRED",
            ),
            description="Test vector index",
            profile=self.profile,
        )
        await temp_index.create(replace=True)
        logger.info("Temporary vector index created.")
        await temp_index.delete(force=True)
        logger.info(
            "Temporary vector index deleted. Attempting to fetch attributes..."
        )
        with pytest.raises(VectorIndexNotFoundError):
            await AsyncVectorIndex(
                index_name="temp_index_for_delete"
            ).get_attributes()
        logger.info("Expected error raised after deleting index.")

    async def test_5310(self):
        """Access attributes after deleting the vector index."""
        logger.info(
            "Testing access to attributes object after deleting "
            "the vector index..."
        )
        temp_index = AsyncVectorIndex(
            index_name="temp_index_for_delete",
            attributes=OracleVectorIndexAttributes(
                location=self.embedding_location,
                object_storage_credential_name="OBJSTORE_CRED",
            ),
            description="Test vector index",
            profile=self.profile,
        )
        await temp_index.create(replace=True)
        logger.info("Fetching attributes before deletion...")
        attrs = await temp_index.get_attributes()
        assert isinstance(attrs, OracleVectorIndexAttributes)
        assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
        assert attrs.location == self.embedding_location
        logger.info("Deleting temporary index...")
        await temp_index.delete(force=True)
        logger.info("Accessing cached attributes after deletion...")
        logger.info("After delete: %s", attrs)
        assert isinstance(attrs, OracleVectorIndexAttributes)
        assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
        assert attrs.location == self.embedding_location
        logger.info("Attributes object remains valid after deletion.")

    async def test_5311(self):
        """get_attributes with empty index name raises error."""
        logger.info("Testing get_attributes() with empty index name...")
        with pytest.raises(AttributeError):
            await AsyncVectorIndex(index_name="").get_attributes()
        logger.info("Empty name correctly raised AttributeError.")

    async def test_5312(self):
        """get_attributes with None as index name raises error."""
        logger.info("Testing get_attributes() with None as index name...")
        with pytest.raises(AttributeError):
            await AsyncVectorIndex(index_name=None).get_attributes()
        logger.info("None name correctly raised AttributeError.")

    async def test_5313(self):
        """get_attributes with special characters in index name."""
        logger.info(
            "Testing get_attributes() with special characters in index name..."
        )
        with pytest.raises(VectorIndexNotFoundError):
            await AsyncVectorIndex(index_name="@@invalid!!").get_attributes()
        logger.info(
            "Special character name correctly raised VectorIndexNotFoundError."
        )

    async def test_5314(self):
        """get_attributes with Unicode index name raises error."""
        logger.info("Testing get_attributes() with Unicode index name...")
        with pytest.raises(VectorIndexNotFoundError):
            await AsyncVectorIndex(index_name="テスト").get_attributes()
        logger.info("Unicode name correctly raised VectorIndexNotFoundError.")

    async def test_5315(self):
        """Multiple indices: check their attribute differences."""
        logger.info(
            "Creating multiple vector indices to compare their attributes..."
        )
        index_a = AsyncVectorIndex(
            index_name="index_a",
            attributes=OracleVectorIndexAttributes(
                location=self.embedding_location,
                object_storage_credential_name="OBJSTORE_CRED",
            ),
            description="Test vector index",
            profile=self.profile,
        )
        index_b = AsyncVectorIndex(
            index_name="index_b",
            attributes=OracleVectorIndexAttributes(
                location=self.embedding_location,
                object_storage_credential_name="OBJSTORE_CRED",
            ),
            description="Test vector index",
            profile=self.profile,
        )
        try:
            logger.info("Creating index_a...")
            await index_a.create(replace=True)
            logger.info("Creating index_b...")
            await index_b.create(replace=True)
            logger.info("Fetching attributes for both indices...")
            attrs_a = await AsyncVectorIndex(index_name="index_a").get_attributes()
            attrs_b = await AsyncVectorIndex(index_name="index_b").get_attributes()
            logger.info("Attrs_a: %s", attrs_a)
            assert attrs_a.pipeline_name != attrs_b.pipeline_name
            logger.info("Indices have distinct pipeline names as expected.")
        finally:
            logger.info("Deleting both indices...")
            for index in (index_a, index_b):
                try:
                    await index.delete(force=True)
                except Exception as exc:
                    logger.warning(
                        "Cleanup failed for %s: %s",
                        index.index_name,
                        exc,
                    )

    async def test_5316(self):
        """Attributes remain consistent after index delete and recreate."""
        logger.info("Testing attributes consistency after delete and recreate...")
        temp_index = AsyncVectorIndex(
            index_name="temp_recreate",
            attributes=OracleVectorIndexAttributes(
                location=self.embedding_location,
                object_storage_credential_name="OBJSTORE_CRED",
            ),
            description="Test vector index",
            profile=self.profile,
        )
        try:
            logger.info("Creating temporary vector index for recreate test...")
            await temp_index.create(replace=True)
            logger.info("Deleting temporary index...")
            await temp_index.delete(force=True)
            logger.info("Recreating temporary index...")
            await temp_index.create(replace=True)
            logger.info("Fetching attributes after recreation...")
            attrs = await AsyncVectorIndex(
                index_name="temp_recreate"
            ).get_attributes()
            assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
            logger.info("Recreate test completed successfully.")
        finally:
            try:
                await temp_index.delete(force=True)
            except Exception as exc:
                logger.warning("Cleanup failed for temp_recreate: %s", exc)

    async def test_5317(self):
        """get_attributes with very long index name raises error."""
        logger.info("Testing get_attributes() with very long index name...")
        long_name = "X" * 100
        with pytest.raises(VectorIndexNotFoundError):
            await AsyncVectorIndex(index_name=long_name).get_attributes()
        logger.info("Long name correctly raised VectorIndexNotFoundError.")

    async def test_5318(self):
        """get_attributes after disconnecting from database raises error."""
        logger.info("Testing get_attributes() after disconnecting from database...")
        await select_ai.async_disconnect()
        with pytest.raises(Exception):
            await AsyncVectorIndex(index_name=self.index_name).get_attributes()
        logger.info("Expected error raised after disconnect.")
        logger.info("Reconnecting for remaining tests...")
        await select_ai.async_connect(**self.reconnect_params)
        assert await select_ai.async_is_connected(), "Connection to DB failed"
        logger.info("Reconnection successful.")

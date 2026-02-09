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
from select_ai import AsyncVectorIndex, OracleVectorIndexAttributes
from select_ai import VectorIndexAttributes
from select_ai.errors import DatabaseNotConnectedError

logger = logging.getLogger("TestAsyncSetVectorIndexAttributes")

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="class")
def set_vec_params(request, vcidx_params):
    request.cls.set_vec_params = vcidx_params


@pytest.fixture(scope="class", autouse=True)
async def setup_and_teardown(request, async_connect, set_vec_params, test_env):
    logger.info("=== Setting up TestAsyncSetVectorIndexAttributes class ===")
    p = request.cls.set_vec_params

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
    request.cls.objstore_cred = "OBJSTORE_CRED"
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

    logger.info("=== Tearing down TestAsyncSetVectorIndexAttributes class ===")
    try:
        vector_index = AsyncVectorIndex(index_name=request.cls.index_name)
        await vector_index.delete(force=True)
    except Exception as exc:
        logger.warning("Warning: drop vector index failed: %s", exc)

    try:
        await request.cls.profile.delete()
    except Exception as exc:
        logger.warning("profile.delete() raised %s unexpectedly.", exc)

    await request.cls.delete_credential()
    logger.info("Teardown complete.\n")


@pytest.fixture(autouse=True)
async def vector_index_state(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    indexes = [
        idx async for idx in AsyncVectorIndex.list(
            index_name_pattern=request.cls.index_name
        )
    ]
    if not indexes:
        logger.info(
            "Vector index %s missing; recreating baseline test state.",
            request.cls.index_name,
        )
        await request.cls.create_credential()
        request.cls.profile = await request.cls.create_profile(
            profile_name=request.cls.profile.profile_name
        )
        await AsyncVectorIndex(
            index_name=request.cls.index_name,
            attributes=request.cls.vector_index_attributes,
            description="Test vector index",
            profile=request.cls.profile,
        ).create(replace=True)
        indexes = [
            idx async for idx in AsyncVectorIndex.list(
                index_name_pattern=request.cls.index_name
            )
        ]
    request.cls.async_vector_index = indexes[0]
    yield
    logger.info("--- Finished test: %s ---", request.function.__name__)


@pytest.mark.usefixtures("set_vec_params", "setup_and_teardown")
class TestAsyncSetVectorIndexAttributes:
    @classmethod
    def get_native_cred_param(cls, cred_name=None) -> dict:
        logger.info("Preparing native credential params for: %s", cred_name)
        p = cls.set_vec_params
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
        p = cls.set_vec_params
        return dict(
            credential_name=cred_name,
            username=p["cred_username"],
            password=p["cred_password"],
        )

    @classmethod
    async def create_credential(
        cls, genai_cred="GENAI_CRED", objstore_cred="OBJSTORE_CRED"
    ):
        logger.info("Creating credentials: %s, %s", genai_cred, objstore_cred)

        genai_credential = cls.get_native_cred_param(genai_cred)
        await select_ai.async_create_credential(
            credential=genai_credential,
            replace=True,
        )

        p = cls.set_vec_params
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
        p = cls.set_vec_params
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
    async def delete_profile(cls, profile):
        return await profile.delete()

    @classmethod
    async def delete_credential(cls):
        try:
            await select_ai.async_delete_credential("GENAI_CRED", force=True)
        except Exception as exc:
            logger.warning("delete_credential() raised %s unexpectedly.", exc)
        try:
            await select_ai.async_delete_credential("OBJSTORE_CRED", force=True)
        except Exception as exc:
            logger.warning("delete_credential() raised %s unexpectedly.", exc)

    async def test_5201(self):
        """Update 'match_limit' attribute."""
        logger.info("Testing update of 'match_limit' attribute...")
        await self.async_vector_index.set_attribute("match_limit", 10)
        attrs = await self.async_vector_index.get_attributes()
        logger.info("Updated match_limit: %s", attrs.match_limit)
        assert attrs.match_limit == 10
        logger.info("Match limit update verified successfully.")

    async def test_5202(self):
        """Update 'similarity_threshold' attribute."""
        logger.info("Testing update of 'similarity_threshold' attribute...")
        await self.async_vector_index.set_attribute(
            "similarity_threshold", 0.8
        )
        attrs = await self.async_vector_index.get_attributes()
        logger.info(
            "Updated similarity_threshold: %s", attrs.similarity_threshold
        )
        assert attrs.similarity_threshold == 0.8
        logger.info("Similarity threshold update verified successfully.")

    async def test_5203(self):
        """Update multiple attributes with VectorIndexAttributes object."""
        logger.info(
            "Testing update of multiple attributes via "
            "VectorIndexAttributes object..."
        )
        update_attrs = VectorIndexAttributes(
            match_limit=5,
            similarity_threshold=0.5,
            location=self.embedding_location,
            refresh_rate=40,
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.set_attributes(attributes=update_attrs)
        logger.info(
            "Expected DatabaseError raised for restricted attribute update: %s",
            exc_info.value,
        )
        assert "ORA-20047" in str(exc_info.value)
        logger.info("Restricted multi-attribute update rejected as expected.")

    async def test_5204(self):
        """Repeated update of the same attribute 'similarity_threshold'."""
        logger.info(
            "Testing repeated update of the same attribute "
            "'similarity_threshold'..."
        )
        await self.async_vector_index.set_attribute(
            "similarity_threshold", 0.8
        )
        await self.async_vector_index.set_attribute(
            "similarity_threshold", 0.5
        )
        attrs = await self.async_vector_index.get_attributes()
        logger.info(
            "Final similarity_threshold value: %s",
            attrs.similarity_threshold,
        )
        assert attrs.similarity_threshold == 0.5
        logger.info("Repeated attribute update verified successfully.")

    async def test_5205(self):
        """Update 'match_limit' with maximum allowed value."""
        logger.info(
            "Testing update of 'match_limit' with maximum allowed value..."
        )
        max_limit = 8192
        await self.async_vector_index.set_attribute("match_limit", max_limit)
        attrs = await self.async_vector_index.get_attributes()
        logger.info("Set match_limit to: %s", attrs.match_limit)
        assert attrs.match_limit == max_limit
        logger.info("Max value for match_limit verified successfully.")

    async def test_5206(self):
        """Update match_limit with minimum value."""
        logger.info("Testing update of match_limit with minimum value...")
        min_limit = 1
        await self.async_vector_index.set_attribute("match_limit", min_limit)
        logger.info(
            "Set match_limit to %s, fetching attributes for verification...",
            min_limit,
        )
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.match_limit == min_limit
        logger.info("match_limit minimum value update verified successfully.")

    async def test_5207(self):
        """Update match_limit with zero value."""
        logger.info("Testing update of match_limit with zero value...")
        min_limit = 0
        await self.async_vector_index.set_attribute("match_limit", min_limit)
        logger.info("Fetching attributes to verify zero value update...")
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.match_limit == min_limit
        logger.info("match_limit zero value update verified successfully.")

    async def test_5208(self):
        """Update profile_name with temporary profile."""
        temp_profile_name = "vector_ai_profile_temp"
        temp_profile = await self.create_profile(profile_name=temp_profile_name)
        logger.info("Temporary profile created: %s", temp_profile_name)
        await self.async_vector_index.set_attribute(
            "profile_name", temp_profile_name
        )
        logger.info(
            "Set profile_name to %s, fetching attributes...",
            temp_profile_name,
        )
        attrs = await self.async_vector_index.get_attributes()
        logger.info(
            "VectorIndex attributes after profile update: %s",
            attrs.__dict__,
        )
        assert attrs.profile_name == temp_profile_name
        vec_index = await AsyncVectorIndex.fetch(self.index_name)
        logger.info(
            "Persisted VectorIndex after profile update: %s",
            vec_index.__dict__,
        )
        assert attrs.profile_name == vec_index.profile.profile_name
        logger.info("Persisted VectorIndex reflects updated profile correctly.")
        await self.delete_profile(temp_profile)
        logger.info("Temporary profile deleted: %s", temp_profile_name)
        await self.async_vector_index.set_attribute(
            "profile_name", self.profile.profile_name
        )
        attrs = await self.async_vector_index.get_attributes()
        logger.info("VectorIndex reset to default profile, verifying...")
        assert attrs.profile_name == self.profile.profile_name
        logger.info("VectorIndex profile reset verified successfully.")

    async def test_5209(self):
        """Update profile_name and then delete profile scenario."""
        logger.info(
            "Testing update of profile_name followed by delete scenario..."
        )
        temp_profile_name = "vector_ai_profile_temp"
        temp_profile = await self.create_profile(profile_name=temp_profile_name)
        logger.info("Temporary profile created: %s", temp_profile_name)
        await self.async_vector_index.set_attribute(
            "profile_name", temp_profile_name
        )
        logger.info(
            "Set profile_name to %s, verifying update...",
            temp_profile_name,
        )
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.profile_name == temp_profile_name
        vec_index = await AsyncVectorIndex.fetch(self.index_name)
        logger.info(
            "Persisted VectorIndex after profile update: %s",
            vec_index.__dict__,
        )
        assert attrs.profile_name == vec_index.profile.profile_name
        await self.delete_profile(temp_profile)
        logger.info("Temporary profile deleted: %s", temp_profile_name)
        logger.info(
            "Verifying VectorIndex retains deleted profile name reference..."
        )
        vec_index = await AsyncVectorIndex.fetch(self.index_name)
        attrs = await vec_index.get_attributes()
        assert attrs.profile_name == temp_profile_name
        logger.info(
            "VectorIndex still references deleted profile name as expected."
        )
        await self.async_vector_index.set_attribute(
            "profile_name", self.profile.profile_name
        )
        attrs = await self.async_vector_index.get_attributes()
        logger.info(
            "Reset VectorIndex profile to default: %s", attrs.__dict__
        )
        assert attrs.profile_name == self.profile.profile_name
        logger.info("Profile reset after delete verified successfully.")

    async def test_5210(self):
        """Deleted profile leaves a stale profile_name on VectorIndex."""
        logger.info("Testing deleted profile behavior via AsyncVectorIndex fetch...")
        temp_profile_name = "vector_ai_profile_temp"
        temp_profile = await self.create_profile(profile_name=temp_profile_name)
        await self.async_vector_index.set_attribute(
            "profile_name", temp_profile_name
        )
        await self.delete_profile(temp_profile)
        vec_index = await AsyncVectorIndex.fetch(self.index_name)
        attrs = await vec_index.get_attributes()
        logger.info(
            "Fetched AsyncVectorIndex after profile delete: profile=%s attrs=%s",
            vec_index.profile,
            attrs.__dict__,
        )
        assert vec_index.profile is None
        assert attrs.profile_name == temp_profile_name
        await self.async_vector_index.set_attribute(
            "profile_name", self.profile.profile_name
        )
        logger.info("Deleted profile behavior verified successfully.")

    async def test_5211(self):
        """Update refresh_rate attribute."""
        logger.info("Testing update of refresh_rate attribute...")
        await self.async_vector_index.set_attribute("refresh_rate", 30)
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.refresh_rate == 30

    async def test_5212(self):
        """Update object_storage_credential_name, handle pipeline."""
        logger.info(
            "Testing update of object_storage_credential_name "
            "with pipeline handling..."
        )
        attrs = await self.async_vector_index.get_attributes()
        pipeline_name = attrs.pipeline_name
        logger.info("Retrieved pipeline name: %s", pipeline_name)
        logger.info("Stopping pipeline: %s", pipeline_name)
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                "BEGIN dbms_cloud_pipeline.stop_pipeline("
                "pipeline_name => :1); END;",
                [pipeline_name],
            )
        logger.info("Pipeline '%s' stopped successfully.", pipeline_name)
        objstore_credential = self.get_cred_param("TEMP_OBJSTORE_CRED")
        logger.info(
            "Creating temporary Object Store credential: TEMP_OBJSTORE_CRED"
        )
        try:
            await select_ai.async_create_credential(
                credential=objstore_credential,
                replace=True,
            )
            logger.info("TEMP_OBJSTORE_CRED created successfully.")
        except Exception as exc:
            raise AssertionError(
                "create_credential() raised an unexpected exception: "
                f"{exc}"
            )
        logger.info("Updating vector index with TEMP_OBJSTORE_CRED...")
        await self.async_vector_index.set_attribute(
            "object_storage_credential_name",
            "TEMP_OBJSTORE_CRED",
        )
        attrs = await self.async_vector_index.get_attributes()
        logger.info("Updated credential: %s", attrs.object_storage_credential_name)
        assert attrs.object_storage_credential_name == "TEMP_OBJSTORE_CRED"
        logger.info("Deleting temporary credential: TEMP_OBJSTORE_CRED")
        try:
            await select_ai.async_delete_credential(
                "TEMP_OBJSTORE_CRED", force=True
            )
            logger.info("TEMP_OBJSTORE_CRED deleted successfully.")
        except Exception as exc:
            pytest.fail(
                f"delete_credential() raised unexpected exception: {exc}"
            )
        logger.info("Restoring original Object Store credential: OBJSTORE_CRED")
        await self.async_vector_index.set_attribute(
            "object_storage_credential_name",
            "OBJSTORE_CRED",
        )
        logger.info("Restarting pipeline: %s", pipeline_name)
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                "BEGIN dbms_cloud_pipeline.start_pipeline("
                "pipeline_name => :1); END;",
                [pipeline_name],
            )
        logger.info("Pipeline '%s' restarted successfully.", pipeline_name)
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
        logger.info("Object Store credential restored successfully.")

    async def test_5213(self):
        """Update object_storage_credential_name with delete handling."""
        logger.info(
            "Testing update of object_storage_credential_name "
            "with delete handling..."
        )
        attrs = await self.async_vector_index.get_attributes()
        pipeline_name = attrs.pipeline_name
        logger.info("Retrieved pipeline name: %s", pipeline_name)
        logger.info("Stopping pipeline: %s", pipeline_name)
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                "BEGIN dbms_cloud_pipeline.stop_pipeline("
                "pipeline_name => :1); END;",
                [pipeline_name],
            )
        logger.info("Pipeline '%s' stopped successfully.", pipeline_name)
        objstore_credential = self.get_cred_param("TEMP_OBJSTORE_CRED")
        logger.info(
            "Creating temporary Object Store credential: TEMP_OBJSTORE_CRED"
        )
        try:
            await select_ai.async_create_credential(
                credential=objstore_credential,
                replace=True,
            )
            logger.info("TEMP_OBJSTORE_CRED created successfully.")
        except Exception as exc:
            raise AssertionError(
                "create_credential() raised an unexpected exception: "
                f"{exc}"
            )
        logger.info("Updating vector index with TEMP_OBJSTORE_CRED...")
        await self.async_vector_index.set_attribute(
            "object_storage_credential_name",
            "TEMP_OBJSTORE_CRED",
        )
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.object_storage_credential_name == "TEMP_OBJSTORE_CRED"
        logger.info(
            "Credential updated to: %s", attrs.object_storage_credential_name
        )
        logger.info("Deleting temporary credential: TEMP_OBJSTORE_CRED")
        try:
            await select_ai.async_delete_credential(
                "TEMP_OBJSTORE_CRED", force=True
            )
            logger.info("TEMP_OBJSTORE_CRED deleted successfully.")
        except Exception as exc:
            pytest.fail(
                f"delete_credential() raised unexpected exception: {exc}"
            )
        logger.info(
            "Verifying that VectorIndex retains deleted credential reference..."
        )
        vec_index = await AsyncVectorIndex.fetch(self.index_name)
        attrs = await vec_index.get_attributes()
        assert attrs.object_storage_credential_name == "TEMP_OBJSTORE_CRED"
        logger.info(
            "VectorIndex still references deleted credential name as expected."
        )
        logger.info("Restoring original Object Store credential: OBJSTORE_CRED")
        await select_ai.async_create_credential(
            credential=self.get_cred_param("OBJSTORE_CRED"),
            replace=True,
        )
        await self.async_vector_index.set_attribute(
            "object_storage_credential_name",
            "OBJSTORE_CRED",
        )
        logger.info("Restarting pipeline: %s", pipeline_name)
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                "BEGIN dbms_cloud_pipeline.start_pipeline("
                "pipeline_name => :1); END;",
                [pipeline_name],
            )
        logger.info("Pipeline '%s' restarted successfully.", pipeline_name)
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
        logger.info(
            "Object Store credential restoration after delete "
            "verified successfully."
        )

    async def test_5214(self):
        """Deleted credential leaves VectorIndex unusable until restored."""
        logger.info("Testing missing credential behavior via AsyncVectorIndex create...")
        temp_credential_name = "TEMP_OBJSTORE_CRED"
        attrs = await self.async_vector_index.get_attributes()
        pipeline_name = attrs.pipeline_name
        logger.info("Stopping pipeline: %s", pipeline_name)
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                "BEGIN dbms_cloud_pipeline.stop_pipeline("
                "pipeline_name => :1); END;",
                [pipeline_name],
            )
        await select_ai.async_create_credential(
            credential=self.get_cred_param(temp_credential_name),
            replace=True,
        )
        await self.async_vector_index.set_attribute(
            "object_storage_credential_name",
            temp_credential_name,
        )
        await select_ai.async_delete_credential(temp_credential_name, force=True)
        failing_index = AsyncVectorIndex(
            index_name="test_vector_index_attr_missing_cred",
            attributes=OracleVectorIndexAttributes(
                location=self.embedding_location,
                object_storage_credential_name=temp_credential_name,
            ),
            description="Missing credential test vector index",
            profile=self.profile,
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await failing_index.create(replace=True)
        logger.info(
            "Expected DatabaseError raised for deleted credential reference: %s",
            exc_info.value,
        )
        assert "ORA-20004" in str(exc_info.value)
        assert temp_credential_name in str(exc_info.value)
        await select_ai.async_create_credential(
            credential=self.get_cred_param("OBJSTORE_CRED"),
            replace=True,
        )
        await self.async_vector_index.set_attribute(
            "object_storage_credential_name",
            "OBJSTORE_CRED",
        )
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(
                "BEGIN dbms_cloud_pipeline.start_pipeline("
                "pipeline_name => :1); END;",
                [pipeline_name],
            )
        logger.info("Deleted credential behavior verified successfully.")

    async def test_5215(self):
        """Update multiple attributes together."""
        logger.info("Testing update of multiple attributes together...")
        updates = {
            "refresh_rate": 50,
            "similarity_threshold": 0.8,
            "match_limit": 10,
        }
        for field, value in updates.items():
            logger.info("Updating %s to %s...", field, value)
            await self.async_vector_index.set_attribute(field, value)
        attrs = await self.async_vector_index.get_attributes()
        logger.info("Fetched attributes after updates: %s", attrs.__dict__)
        assert attrs.refresh_rate == updates["refresh_rate"]
        assert attrs.similarity_threshold == updates["similarity_threshold"]
        assert attrs.match_limit == updates["match_limit"]
        logger.info("All multiple attribute updates verified successfully.")

    async def test_5216(self):
        """Update description (should raise DatabaseError)."""
        logger.info(
            "Testing update of description attribute "
            "(should raise DatabaseError)..."
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.set_attribute(
                "description", "updated description"
            )
        assert "ORA-20048" in str(exc_info.value)
        logger.info(
            "DatabaseError correctly raised for invalid description update."
        )

    async def test_5217(self):
        """Update pipeline_name (should raise DatabaseError)."""
        logger.info(
            "Testing update of pipeline_name (expected DatabaseError)..."
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.set_attribute(
                "pipeline_name", "test_pipeline"
            )
        assert "ORA-20048" in str(exc_info.value)
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.pipeline_name == "TEST_VECTOR_INDEX_ATTR$VECPIPELINE"
        logger.info(
            "Pipeline update correctly raised error and original value retained."
        )

    async def test_5218(self):
        """Update chunk_size (should fail)."""
        logger.info(
            "Testing update of chunk_size (should fail with ORA-20047)..."
        )
        attrs = await self.async_vector_index.get_attributes()
        original_chunk_size = attrs.chunk_size
        logger.info("Current attributes: %s", attrs.__dict__)
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.set_attribute("chunk_size", 2048)
        assert "ORA-20047" in str(exc_info.value)
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.chunk_size == original_chunk_size
        logger.info(
            "chunk_size update prevented successfully; original value "
            "verified."
        )

    async def test_5219(self):
        """Update chunk_overlap (should fail)."""
        logger.info(
            "Testing update of chunk_overlap (should fail with ORA-20047)..."
        )
        original_chunk_overlap = (
            await self.async_vector_index.get_attributes()
        ).chunk_overlap
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.set_attribute("chunk_overlap", 256)
        assert "ORA-20047" in str(exc_info.value)
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.chunk_overlap == original_chunk_overlap
        logger.info(
            "chunk_overlap update prevented successfully; original value "
            "verified."
        )

    async def test_5220(self):
        """Update vector_distance_metric (should fail)."""
        logger.info(
            "Testing update of vector_distance_metric "
            "(should fail with ORA-20047)..."
        )
        original_distance_metric = (
            await self.async_vector_index.get_attributes()
        ).vector_distance_metric
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.set_attribute(
                "vector_distance_metric", "EUCLIDEAN"
            )
        assert "ORA-20047" in str(exc_info.value)
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.vector_distance_metric == original_distance_metric
        logger.info("vector_distance_metric update prevented successfully.")

    async def test_5221(self):
        """Partial update with VectorIndexAttributes object."""
        logger.info(
            "Testing partial update with VectorIndexAttributes object..."
        )
        update_attrs = VectorIndexAttributes(match_limit=20, chunk_size=2048)
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.set_attributes(attributes=update_attrs)
        logger.info(
            "Expected DatabaseError raised for partial restricted update: %s",
            exc_info.value,
        )
        assert "ORA-20047" in str(exc_info.value)
        attrs = await self.async_vector_index.get_attributes()
        logger.info("Attributes after update attempt: %s", attrs.__dict__)
        logger.info("Partial restricted update rejected as expected.")

    async def test_5222(self):
        """Update with invalid attribute combinations."""
        logger.info("Testing update with invalid attribute combinations...")
        update_attrs = VectorIndexAttributes(
            chunk_size=2048,
            chunk_overlap=256,
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.set_attributes(attributes=update_attrs)
        logger.info(
            "Expected DatabaseError raised for invalid attribute combination: %s",
            exc_info.value,
        )
        assert "ORA-20047" in str(exc_info.value)
        attrs = await self.async_vector_index.get_attributes()
        logger.info("Attributes after invalid update: %s", attrs.__dict__)
        logger.info("Invalid update combination rejected as expected.")

    async def test_5223(self):
        """Update location (should raise ORA-20047)."""
        logger.info("Testing update of location (expected ORA-20047)...")
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.set_attribute(
                "location", self.embedding_location
            )
        assert "ORA-20047" in str(exc_info.value)
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.location == self.embedding_location
        logger.info("Location update prevented successfully.")

    async def test_5224(self):
        """Update using profile object directly."""
        logger.info(
            "Testing update of vector index using profile object directly..."
        )
        temp_profile_name = "vector_ai_profile_temp"
        temp_profile = await self.create_profile(profile_name=temp_profile_name)
        logger.info("Created temporary profile: %s", temp_profile_name)
        try:
            await self.async_vector_index.set_attribute("profile", temp_profile)
        except oracledb.NotSupportedError as exc:
            logger.info("Expected NotSupportedError caught: %s", exc)
        except Exception as exc:
            raise AssertionError(f"Unexpected exception: {exc}")
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.profile_name in [
            self.profile.profile_name,
            temp_profile_name,
        ]
        logger.info(
            "Attributes after attempted profile object update: %s",
            attrs.__dict__,
        )
        try:
            await self.delete_profile(temp_profile)
            logger.info(
                "Temporary profile '%s' deleted successfully.",
                temp_profile_name,
            )
        except Exception as exc:
            logger.warning("Profile cleanup failed: %s", exc)

    async def test_5225(self):
        """Update with invalid attribute name."""
        logger.info("Testing update with invalid attribute name...")
        with pytest.raises(oracledb.DatabaseError):
            await self.async_vector_index.set_attribute("invalid_attr", "value")
        logger.info("Invalid attribute name correctly raised DatabaseError.")

    async def test_5226(self):
        """Update with invalid type for integer field."""
        logger.info("Testing update with invalid type for integer field...")
        with pytest.raises(oracledb.DatabaseError):
            await self.async_vector_index.set_attribute(
                "chunk_size", "not_an_int"
            )
        logger.info("Invalid integer type correctly raised DatabaseError.")

    async def test_5227(self):
        """Update with invalid type for float field."""
        logger.info("Testing update with invalid type for float field...")
        with pytest.raises(oracledb.DatabaseError):
            await self.async_vector_index.set_attribute(
                "similarity_threshold", "NaN"
            )
        logger.info("Invalid float type correctly raised DatabaseError.")

    async def test_5228(self):
        """Update with invalid enum value for vector_distance_metric."""
        logger.info(
            "Testing update with invalid enum value "
            "for vector_distance_metric..."
        )
        with pytest.raises(oracledb.DatabaseError):
            await self.async_vector_index.set_attribute(
                "vector_distance_metric", "INVALID"
            )
        logger.info("Invalid enum value correctly raised DatabaseError.")

    async def test_5229(self):
        """Update on nonexistent vector index."""
        logger.info("Testing update on nonexistent vector index...")
        temp_index = AsyncVectorIndex(index_name="does_not_exist")
        with pytest.raises(AttributeError):
            await temp_index.set_attribute("chunk_size", 512)
        logger.info(
            "Nonexistent index update correctly raised AttributeError."
        )

    async def test_5230(self):
        """Update with None as attribute name (should fail)."""
        logger.info("Testing update with None as attribute name...")
        with pytest.raises(TypeError):
            await self.async_vector_index.set_attribute(None, 128)
        logger.info("None attribute name correctly raised TypeError.")

    async def test_5231(self):
        """Update with None as attribute name for second time."""
        logger.info(
            "Testing update with None as attribute name for second time..."
        )
        with pytest.raises(TypeError):
            await self.async_vector_index.set_attribute(None, 128)
        logger.info("None attribute name correctly raised TypeError.")

    async def test_5232(self):
        """Update with invalid attributes object (non-object input)."""
        logger.info(
            "Testing update with invalid attributes object "
            "(non-object input)..."
        )
        with pytest.raises(AttributeError):
            await self.async_vector_index.set_attributes(
                attributes="not_an_object"
            )
        logger.info(
            "Invalid attributes object correctly raised AttributeError."
        )

    async def test_5233(self):
        """Update after disconnecting from the database."""
        logger.info("Testing update after disconnecting from the database...")
        await select_ai.async_disconnect()
        with pytest.raises(DatabaseNotConnectedError):
            await self.async_vector_index.set_attribute("chunk_size", 256)
        logger.info(
            "DatabaseNotConnectedError correctly raised after disconnect."
        )
        logger.info("Reconnecting for further tests...")
        await select_ai.async_connect(**self.reconnect_params)
        assert await select_ai.async_is_connected(), (
            "Connection to DB failed"
        )
        logger.info("Reconnection successful.")

    async def test_5234(self):
        """Update with None as attribute value (should fail)."""
        logger.info("Testing update with None as attribute value...")
        with pytest.raises(oracledb.DatabaseError):
            await self.async_vector_index.set_attribute("chunk_size", None)
        logger.info("None value correctly raised DatabaseError.")

    async def test_5235(self):
        """Concurrent updates on the same vector index."""
        logger.info("Testing concurrent updates on the same vector index...")
        index1 = await AsyncVectorIndex.fetch(self.index_name)
        index2 = await AsyncVectorIndex.fetch(self.index_name)
        await index1.set_attribute("match_limit", 15)
        await index2.set_attribute("match_limit", 20)
        attrs = await self.async_vector_index.get_attributes()
        logger.info(
            "Final match_limit value after concurrent updates: %s",
            attrs.match_limit,
        )
        assert attrs.match_limit in [15, 20]
        logger.info(
            "Concurrent update behavior verified (last writer wins)."
        )

    async def test_5236(self):
        """Update with excessively large attribute value."""
        logger.info("Testing update with excessively large attribute value...")
        long_name = "X" * 500
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.async_vector_index.set_attribute("profile_name", long_name)
        assert "ORA-20048" in str(exc_info.value)
        logger.info("Large attribute value correctly raised DatabaseError.")

    async def test_5237(self):
        """Repeated updates to match_limit (last writer wins)."""
        logger.info("Testing repeated updates to match_limit...")
        for i in range(5):
            await self.async_vector_index.set_attribute("match_limit", i * 10)
            logger.info("Set match_limit to %s", i * 10)
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.match_limit == 40
        logger.info("Repeated update test passed; last value retained.")

    async def test_5238(self):
        """Update attribute after delete and recreate of vector index."""
        logger.info(
            "Testing attribute update after deleting and recreating the "
            "vector index..."
        )
        await self.async_vector_index.delete(force=True)
        logger.info("Vector index deleted.")
        self.async_vector_index = AsyncVectorIndex(
            index_name=self.index_name,
            attributes=self.vector_index_attributes,
            description="Test vector index",
            profile=self.profile,
        )
        await self.async_vector_index.create(replace=True)
        logger.info("Vector index recreated.")
        await self.async_vector_index.set_attribute("match_limit", 10)
        attrs = await self.async_vector_index.get_attributes()
        assert attrs.match_limit == 10
        logger.info("Update after recreation verified successfully.")

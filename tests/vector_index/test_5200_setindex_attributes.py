# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------


import logging
import os
import oracledb
import pytest
import select_ai
from select_ai import VectorIndex, VectorIndexAttributes, OracleVectorIndexAttributes
from select_ai.errors import DatabaseNotConnectedError

logger = logging.getLogger("TestSetVectorIndexAttributes")


@pytest.fixture(scope="class", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO
    )


@pytest.fixture(scope="class")
def set_vec_params(
    request,
    vcidx_params,
):
    request.cls.set_vec_params = vcidx_params


@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown(request, connect, set_vec_params, oci_credential):
    logger.info("=== Setting up TestSetVectorIndexAttributes class ===")
    p = request.cls.set_vec_params

    # 'connect' fixture from base tests/conftest.py ensures DB connection exists.
    # Do NOT disconnect here; let the session fixture own lifecycle.
    assert select_ai.is_connected(), "Connection to DB failed"

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
    request.cls.shared_oci_credential = oci_credential

    logger.info("Fetching credential secrets and OCI configuration...")
    request.cls.create_credential()
    request.cls.profile = request.cls.create_profile()
    logger.info("Profile 'vector_ai_profile' created successfully.")

    request.cls.index_name = "test_vector_index_attr"
    vi_attrs = OracleVectorIndexAttributes(
        location=p["embedding_location"],
        object_storage_credential_name="OBJSTORE_CRED"
    )
    request.cls.vector_index_attributes = vi_attrs

    vi = VectorIndex(
        index_name=request.cls.index_name,
        attributes=vi_attrs,
        description="Test vector index",
        profile=request.cls.profile
    )
    vi.create(replace=True)

    # Keep original validation intent (handle either classmethod or instance list())
    try:
        created_indexes = [idx.index_name for idx in VectorIndex.list()]
    except Exception:
        created_indexes = [idx.index_name for idx in VectorIndex().list()]
    assert request.cls.index_name.upper() in created_indexes, f"VectorIndex {request.cls.index_name} was not created"

    yield

    logger.info("=== Tearing down TestSetVectorIndexAttributes class ===")
    try:
        vector_index = VectorIndex(index_name=request.cls.index_name)
        vector_index.delete(force=True)
    except Exception as e:
        logger.warning(f"Warning: drop vector index failed: {e}")

    try:
        request.cls.profile.delete()
    except Exception as e:
        logger.warning(f"profile.delete() raised {e} unexpectedly.")

    request.cls.delete_credential()
    request.cls.ensure_session_oci_credential()
    logger.info("Teardown complete.\n")


@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info(f"--- Starting test: {request.function.__name__} ---")
    yield
    logger.info(f"--- Finished test: {request.function.__name__} ---")


@pytest.mark.usefixtures("set_vec_params", "setup_and_teardown")
class TestSetVectorIndexAttributes:
    @classmethod
    def get_native_cred_param(cls, cred_name=None) -> dict:
        logger.info(f"Preparing native credential params for: {cred_name}")
        p = cls.set_vec_params
        return dict(
            credential_name=cred_name,
            user_ocid=p["user_ocid"],
            tenancy_ocid=p["tenancy_ocid"],
            private_key=p["private_key"],
            fingerprint=p["fingerprint"]
        )

    @classmethod
    def get_cred_param(cls, cred_name=None) -> dict:
        logger.info(f"Preparing basic credential params for: {cred_name}")
        p = cls.set_vec_params
        return dict(
            credential_name=cred_name,
            username=p["cred_username"],
            password=p["cred_password"]
        )

    @classmethod
    def create_credential(cls, genai_cred="GENAI_CRED", objstore_cred="OBJSTORE_CRED"):
        logger.info(f"Creating credentials: {genai_cred}, {objstore_cred}")

        genai_credential = cls.get_native_cred_param(genai_cred)
        select_ai.create_credential(credential=genai_credential, replace=True)

        # Only create OBJSTORE_CRED if creds are provided in env
        p = cls.set_vec_params
        if p.get("cred_username") and p.get("cred_password"):
            objstore_credential = cls.get_cred_param(objstore_cred)
            select_ai.create_credential(credential=objstore_credential, replace=True)
            logger.info("Credentials created.")
        else:
            logger.info("Skipping ObjectStore credential creation (CRED_USERNAME/CRED_PASSWORD not set).")

    @classmethod
    def create_profile(cls, profile_name="vector_ai_profile"):
        p = cls.set_vec_params
        return select_ai.Profile(
            profile_name=profile_name,
            attributes=select_ai.ProfileAttributes(
                credential_name="GENAI_CRED",
                provider=select_ai.OCIGenAIProvider(
                    oci_compartment_id=p["oci_compartment_id"],
                    oci_apiformat="GENERIC",
                    embedding_model="cohere.embed-english-v3.0",
                )
            ),
            description="OCI GENAI Profile",
            replace=True
        )

    @classmethod
    def delete_profile(cls, profile):
        return profile.delete()

    @classmethod
    def delete_credential(cls):
        try:
            select_ai.delete_credential("GENAI_CRED", force=True)
        except Exception as e:
            logger.warning(f"delete_credential() raised {e} unexpectedly.")
        try:
            select_ai.delete_credential("OBJSTORE_CRED", force=True)
        except Exception as e:
            logger.warning(f"delete_credential() raised {e} unexpectedly.")

    @classmethod
    def ensure_session_oci_credential(cls):
        credential_name = cls.shared_oci_credential["credential_name"]
        select_ai.create_credential(
            credential={
                "credential_name": credential_name,
                "user_ocid": cls.user_ocid,
                "tenancy_ocid": cls.tenancy_ocid,
                "private_key": cls.private_key,
                "fingerprint": cls.fingerprint,
            },
            replace=True,
        )
        logger.info(
            "Recreated shared OCI credential for session teardown: %s",
            credential_name,
        )

    def setup_method(self, method):
        logger.info(f"SetUp for {method.__name__}")
        vecidx = VectorIndex()
        indexes = list(vecidx.list(index_name_pattern=self.index_name))
        if not indexes:
            logger.info(
                "Vector index %s missing; recreating baseline test state.",
                self.index_name,
            )
            self.create_credential()
            self.profile = self.create_profile(profile_name=self.profile.profile_name)
            VectorIndex(
                index_name=self.index_name,
                attributes=self.vector_index_attributes,
                description="Test vector index",
                profile=self.profile,
            ).create(replace=True)
            indexes = list(vecidx.list(index_name_pattern=self.index_name))
        self.vector_index = indexes[0]

    def teardown_method(self, method):
        logger.info(f"TearDown for {method.__name__}")

    def test_5201(self):
        """Update 'match_limit' attribute."""
        logger.info("Testing update of 'match_limit' attribute...")
        self.vector_index.set_attribute("match_limit", 10)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Updated match_limit: {attrs.match_limit}")
        assert attrs.match_limit == 10
        logger.info("Match limit update verified successfully.")

    def test_5202(self):
        """Update 'similarity_threshold' attribute."""
        logger.info("Testing update of 'similarity_threshold' attribute...")
        self.vector_index.set_attribute("similarity_threshold", 0.8)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Updated similarity_threshold: {attrs.similarity_threshold}")
        assert attrs.similarity_threshold == 0.8
        logger.info("Similarity threshold update verified successfully.")

    def test_5203(self):
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
            self.vector_index.set_attributes(attributes=update_attrs)
        logger.info(
            "Expected DatabaseError raised for restricted attribute update: %s",
            exc_info.value,
        )
        assert "ORA-20047" in str(exc_info.value)
        logger.info("Restricted multi-attribute update rejected as expected.")

    def test_5204(self):
        """Repeated update of the same attribute 'similarity_threshold'."""
        logger.info("Testing repeated update of the same attribute 'similarity_threshold'...")
        self.vector_index.set_attribute("similarity_threshold", 0.8)
        self.vector_index.set_attribute("similarity_threshold", 0.5)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Final similarity_threshold value: {attrs.similarity_threshold}")
        assert attrs.similarity_threshold == 0.5
        logger.info("Repeated attribute update verified successfully.")

    def test_5205(self):
        """Update 'match_limit' with maximum allowed value."""
        logger.info("Testing update of 'match_limit' with maximum allowed value...")
        max_limit = 8192
        self.vector_index.set_attribute("match_limit", max_limit)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Set match_limit to: {attrs.match_limit}")
        assert attrs.match_limit == max_limit
        logger.info("Max value for match_limit verified successfully.")

    def test_5206(self):
        """Update match_limit with minimum value."""
        logger.info("Testing update of match_limit with minimum value...")
        min_limit = 1
        self.vector_index.set_attribute("match_limit", min_limit)
        logger.info(f"Set match_limit to {min_limit}, fetching attributes for verification...")
        attrs = self.vector_index.get_attributes()
        assert attrs.match_limit == min_limit
        logger.info("match_limit minimum value update verified successfully.")

    def test_5207(self):
        """Update match_limit with zero value."""
        logger.info("Testing update of match_limit with zero value...")
        min_limit = 0
        self.vector_index.set_attribute("match_limit", min_limit)
        logger.info("Fetching attributes to verify zero value update...")
        attrs = self.vector_index.get_attributes()
        assert attrs.match_limit == min_limit
        logger.info("match_limit zero value update verified successfully.")

    def test_5208(self):
        """Update profile_name with temporary profile."""
        temp_profile_name = "vector_ai_profile_temp"
        temp_profile = self.create_profile(profile_name=temp_profile_name)
        logger.info(f"Temporary profile created: {temp_profile_name}")
        self.vector_index.set_attribute("profile_name", temp_profile_name)
        logger.info(f"Set profile_name to {temp_profile_name}, fetching attributes...")
        attrs = self.vector_index.get_attributes()
        logger.info(f"VectorIndex attributes after profile update: {attrs.__dict__}")
        assert attrs.profile_name == temp_profile_name
        vecidx = VectorIndex()
        vec_index = (list(vecidx.list(index_name_pattern=self.index_name)))[0]
        logger.info(f"Persisted VectorIndex after profile update: {vec_index.__dict__}")
        assert attrs.profile_name == vec_index.profile.profile_name
        logger.info("Persisted VectorIndex reflects updated profile correctly.")
        self.delete_profile(temp_profile)
        logger.info(f"Temporary profile deleted: {temp_profile_name}")
        self.vector_index.set_attribute("profile_name", self.profile.profile_name)
        attrs = self.vector_index.get_attributes()
        logger.info("VectorIndex reset to default profile, verifying...")
        assert attrs.profile_name == self.profile.profile_name
        logger.info("VectorIndex profile reset verified successfully.")

    def test_5209(self):
        """Update profile_name and then delete profile scenario."""
        logger.info(
            "Testing update of profile_name followed by delete scenario..."
        )
        temp_profile_name = "vector_ai_profile_temp"
        temp_profile = self.create_profile(profile_name=temp_profile_name)
        logger.info(f"Temporary profile created: {temp_profile_name}")
        self.vector_index.set_attribute("profile_name", temp_profile_name)
        logger.info(f"Set profile_name to {temp_profile_name}, verifying update...")
        attrs = self.vector_index.get_attributes()
        assert attrs.profile_name == temp_profile_name
        vecidx = VectorIndex()
        vec_index = (list(vecidx.list(index_name_pattern=self.index_name)))[0]
        logger.info(f"Persisted VectorIndex after profile update: {vec_index.__dict__}")
        assert attrs.profile_name == vec_index.profile.profile_name
        self.delete_profile(temp_profile)
        logger.info(f"Temporary profile deleted: {temp_profile_name}")
        logger.info(
            "Verifying VectorIndex retains deleted profile name reference..."
        )
        vecidx = VectorIndex()
        vec_index = (list(vecidx.list(index_name_pattern=self.index_name)))[0]
        attrs = vec_index.get_attributes()
        assert attrs.profile_name == temp_profile_name
        logger.info(
            "VectorIndex still references deleted profile name as expected."
        )
        self.vector_index.set_attribute("profile_name", self.profile.profile_name)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Reset VectorIndex profile to default: {attrs.__dict__}")
        assert attrs.profile_name == self.profile.profile_name
        logger.info("Profile reset after delete verified successfully.")

    def test_5210(self):
        """Deleted profile leaves a stale profile_name on VectorIndex."""
        logger.info("Testing deleted profile behavior via VectorIndex fetch...")
        temp_profile_name = "vector_ai_profile_temp"
        temp_profile = self.create_profile(profile_name=temp_profile_name)
        self.vector_index.set_attribute("profile_name", temp_profile_name)
        self.delete_profile(temp_profile)
        vec_index = VectorIndex.fetch(self.index_name)
        attrs = vec_index.get_attributes()
        logger.info(
            "Fetched VectorIndex after profile delete: profile=%s attrs=%s",
            vec_index.profile,
            attrs.__dict__,
        )
        assert vec_index.profile is None
        assert attrs.profile_name == temp_profile_name
        self.vector_index.set_attribute("profile_name", self.profile.profile_name)
        logger.info("Deleted profile behavior verified successfully.")

    def test_5211(self):
        """Update refresh_rate attribute."""
        logger.info("Testing update of refresh_rate attribute...")
        self.vector_index.set_attribute("refresh_rate", 30)
        attrs = self.vector_index.get_attributes()
        assert attrs.refresh_rate == 30

    def test_5212(self):
        """Update object_storage_credential_name, handle pipeline."""
        logger.info("Testing update of object_storage_credential_name with pipeline handling...")
        attrs = self.vector_index.get_attributes()
        pipeline_name = attrs.pipeline_name
        logger.info(f"Retrieved pipeline name: {pipeline_name}")
        logger.info(f"Stopping pipeline: {pipeline_name}")
        with select_ai.cursor() as cursor:
            cursor.execute("BEGIN dbms_cloud_pipeline.stop_pipeline(pipeline_name => :1); END;", [pipeline_name])
        logger.info(f"Pipeline '{pipeline_name}' stopped successfully.")
        objstore_credential = self.get_cred_param("TEMP_OBJSTORE_CRED")
        logger.info("Creating temporary Object Store credential: TEMP_OBJSTORE_CRED")
        try:
            select_ai.create_credential(credential=objstore_credential, replace=True)
            logger.info("TEMP_OBJSTORE_CRED created successfully.")
        except Exception as e:
            raise AssertionError(f"create_credential() raised an unexpected exception: {e}")
        logger.info("Updating vector index with TEMP_OBJSTORE_CRED...")
        self.vector_index.set_attribute("object_storage_credential_name", "TEMP_OBJSTORE_CRED")
        attrs = self.vector_index.get_attributes()
        logger.info(f"Updated credential: {attrs.object_storage_credential_name}")
        assert attrs.object_storage_credential_name == "TEMP_OBJSTORE_CRED"
        logger.info("Deleting temporary credential: TEMP_OBJSTORE_CRED")
        try:
            select_ai.delete_credential("TEMP_OBJSTORE_CRED", force=True)
            logger.info("TEMP_OBJSTORE_CRED deleted successfully.")
        except Exception as e:
            pytest.fail(f"delete_credential() raised unexpected exception: {e}")
        logger.info("Restoring original Object Store credential: OBJSTORE_CRED")
        self.vector_index.set_attribute("object_storage_credential_name", "OBJSTORE_CRED")
        logger.info(f"Restarting pipeline: {pipeline_name}")
        with select_ai.cursor() as cursor:
            cursor.execute("BEGIN dbms_cloud_pipeline.start_pipeline(pipeline_name => :1); END;", [pipeline_name])
        logger.info(f"Pipeline '{pipeline_name}' restarted successfully.")
        attrs = self.vector_index.get_attributes()
        assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
        logger.info("Object Store credential restored successfully.")

    def test_5213(self):
        """Update object_storage_credential_name with delete handling."""
        logger.info("Testing update of object_storage_credential_name with delete handling...")
        attrs = self.vector_index.get_attributes()
        pipeline_name = attrs.pipeline_name
        logger.info(f"Retrieved pipeline name: {pipeline_name}")
        logger.info(f"Stopping pipeline: {pipeline_name}")
        with select_ai.cursor() as cursor:
            cursor.execute("BEGIN dbms_cloud_pipeline.stop_pipeline(pipeline_name => :1); END;", [pipeline_name])
        logger.info(f"Pipeline '{pipeline_name}' stopped successfully.")
        objstore_credential = self.get_cred_param("TEMP_OBJSTORE_CRED")
        logger.info("Creating temporary Object Store credential: TEMP_OBJSTORE_CRED")
        try:
            select_ai.create_credential(credential=objstore_credential, replace=True)
            logger.info("TEMP_OBJSTORE_CRED created successfully.")
        except Exception as e:
            raise AssertionError(f"create_credential() raised an unexpected exception: {e}")
        logger.info("Updating vector index with TEMP_OBJSTORE_CRED...")
        self.vector_index.set_attribute("object_storage_credential_name", "TEMP_OBJSTORE_CRED")
        attrs = self.vector_index.get_attributes()
        assert attrs.object_storage_credential_name == "TEMP_OBJSTORE_CRED"
        logger.info(f"Credential updated to: {attrs.object_storage_credential_name}")
        logger.info("Deleting temporary credential: TEMP_OBJSTORE_CRED")
        try:
            select_ai.delete_credential("TEMP_OBJSTORE_CRED", force=True)
            logger.info("TEMP_OBJSTORE_CRED deleted successfully.")
        except Exception as e:
            pytest.fail(f"delete_credential() raised unexpected exception: {e}")
        logger.info(
            "Verifying that VectorIndex retains deleted credential reference..."
        )
        vecidx = VectorIndex()
        vec_index = (list(vecidx.list(index_name_pattern=self.index_name)))[0]
        attrs = vec_index.get_attributes()
        assert attrs.object_storage_credential_name == "TEMP_OBJSTORE_CRED"
        logger.info(
            "VectorIndex still references deleted credential name as expected."
        )
        logger.info("Restoring original Object Store credential: OBJSTORE_CRED")
        self.get_cred_param("OBJSTORE_CRED")
        select_ai.create_credential(
            credential=self.get_cred_param("OBJSTORE_CRED"),
            replace=True,
        )
        self.vector_index.set_attribute("object_storage_credential_name", "OBJSTORE_CRED")
        logger.info(f"Restarting pipeline: {pipeline_name}")
        with select_ai.cursor() as cursor:
            cursor.execute("BEGIN dbms_cloud_pipeline.start_pipeline(pipeline_name => :1); END;", [pipeline_name])
        logger.info(f"Pipeline '{pipeline_name}' restarted successfully.")
        attrs = self.vector_index.get_attributes()
        assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
        logger.info("Object Store credential restoration after delete verified successfully.")

    def test_5214(self):
        """Deleted credential leaves VectorIndex unusable until restored."""
        logger.info("Testing missing credential behavior via VectorIndex create...")
        temp_credential_name = "TEMP_OBJSTORE_CRED"
        attrs = self.vector_index.get_attributes()
        pipeline_name = attrs.pipeline_name
        logger.info("Stopping pipeline: %s", pipeline_name)
        with select_ai.cursor() as cursor:
            cursor.execute(
                "BEGIN dbms_cloud_pipeline.stop_pipeline(pipeline_name => :1); END;",
                [pipeline_name],
            )
        select_ai.create_credential(
            credential=self.get_cred_param(temp_credential_name),
            replace=True,
        )
        self.vector_index.set_attribute(
            "object_storage_credential_name",
            temp_credential_name,
        )
        select_ai.delete_credential(temp_credential_name, force=True)
        failing_index = VectorIndex(
            index_name="test_vector_index_attr_missing_cred",
            attributes=OracleVectorIndexAttributes(
                location=self.embedding_location,
                object_storage_credential_name=temp_credential_name,
            ),
            description="Missing credential test vector index",
            profile=self.profile,
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            failing_index.create(replace=True)
        logger.info(
            "Expected DatabaseError raised for deleted credential reference: %s",
            exc_info.value,
        )
        assert "ORA-20004" in str(exc_info.value)
        assert temp_credential_name in str(exc_info.value)
        select_ai.create_credential(
            credential=self.get_cred_param("OBJSTORE_CRED"),
            replace=True,
        )
        self.vector_index.set_attribute(
            "object_storage_credential_name",
            "OBJSTORE_CRED",
        )
        with select_ai.cursor() as cursor:
            cursor.execute(
                "BEGIN dbms_cloud_pipeline.start_pipeline(pipeline_name => :1); END;",
                [pipeline_name],
            )
        logger.info("Deleted credential behavior verified successfully.")

    def test_5215(self):
        """Update multiple attributes together."""
        logger.info("Testing update of multiple attributes together...")
        updates = {
            "refresh_rate": 50,
            "similarity_threshold": 0.8,
            "match_limit": 10
        }
        for field, value in updates.items():
            logger.info(f"Updating {field} to {value}...")
            self.vector_index.set_attribute(field, value)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Fetched attributes after updates: {attrs.__dict__}")
        assert attrs.refresh_rate == updates["refresh_rate"]
        assert attrs.similarity_threshold == updates["similarity_threshold"]
        assert attrs.match_limit == updates["match_limit"]
        logger.info("All multiple attribute updates verified successfully.")

    def test_5216(self):
        """Update description (should raise DatabaseError)."""
        logger.info("Testing update of description attribute (should raise DatabaseError)...")
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            self.vector_index.set_attribute("description", "updated description")
        assert "ORA-20048" in str(exc_info.value)
        logger.info("DatabaseError correctly raised for invalid description update.")

    def test_5217(self):
        """Update pipeline_name (should raise DatabaseError)."""
        logger.info("Testing update of pipeline_name (expected DatabaseError)...")
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            self.vector_index.set_attribute("pipeline_name", "test_pipeline")
        assert "ORA-20048" in str(exc_info.value)
        attrs = self.vector_index.get_attributes()
        assert attrs.pipeline_name == "TEST_VECTOR_INDEX_ATTR$VECPIPELINE"
        logger.info("Pipeline update correctly raised error and original value retained.")

    def test_5218(self):
        """Update chunk_size (should fail)."""
        logger.info("Testing update of chunk_size (should fail with ORA-20047)...")
        attrs = self.vector_index.get_attributes()
        original_chunk_size = attrs.chunk_size
        logger.info(f"Current attributes: {attrs.__dict__}")
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            self.vector_index.set_attribute("chunk_size", 2048)
        assert "ORA-20047" in str(exc_info.value)
        attrs = self.vector_index.get_attributes()
        assert attrs.chunk_size == original_chunk_size
        logger.info("chunk_size update prevented successfully; original value verified.")

    def test_5219(self):
        """Update chunk_overlap (should fail)."""
        logger.info("Testing update of chunk_overlap (should fail with ORA-20047)...")
        original_chunk_overlap = self.vector_index.get_attributes().chunk_overlap
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            self.vector_index.set_attribute("chunk_overlap", 256)
        assert "ORA-20047" in str(exc_info.value)
        attrs = self.vector_index.get_attributes()
        assert attrs.chunk_overlap == original_chunk_overlap
        logger.info("chunk_overlap update prevented successfully; original value verified.")

    def test_5220(self):
        """Update vector_distance_metric (should fail)."""
        logger.info("Testing update of vector_distance_metric (should fail with ORA-20047)...")
        original_distance_metric = (
            self.vector_index.get_attributes().vector_distance_metric
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            self.vector_index.set_attribute("vector_distance_metric", "EUCLIDEAN")
        assert "ORA-20047" in str(exc_info.value)
        attrs = self.vector_index.get_attributes()
        assert attrs.vector_distance_metric == original_distance_metric
        logger.info("vector_distance_metric update prevented successfully.")

    def test_5221(self):
        """Partial update with VectorIndexAttributes object."""
        logger.info("Testing partial update with VectorIndexAttributes object...")
        update_attrs = VectorIndexAttributes(match_limit=20, chunk_size=2048)
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            self.vector_index.set_attributes(attributes=update_attrs)
        logger.info(
            "Expected DatabaseError raised for partial restricted update: %s",
            exc_info.value,
        )
        assert "ORA-20047" in str(exc_info.value)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Attributes after update attempt: {attrs.__dict__}")
        logger.info("Partial restricted update rejected as expected.")

    def test_5222(self):
        """Update with invalid attribute combinations."""
        logger.info("Testing update with invalid attribute combinations...")
        update_attrs = VectorIndexAttributes(chunk_size=2048, chunk_overlap=256)
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            self.vector_index.set_attributes(attributes=update_attrs)
        logger.info(
            "Expected DatabaseError raised for invalid attribute combination: %s",
            exc_info.value,
        )
        assert "ORA-20047" in str(exc_info.value)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Attributes after invalid update: {attrs.__dict__}")
        logger.info("Invalid update combination rejected as expected.")

    def test_5223(self):
        """Update location (should raise ORA-20047)."""
        logger.info("Testing update of location (expected ORA-20047)...")
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            self.vector_index.set_attribute("location", self.embedding_location)
        assert "ORA-20047" in str(exc_info.value)
        attrs = self.vector_index.get_attributes()
        assert attrs.location == self.embedding_location
        logger.info("Location update prevented successfully.")

    def test_5224(self):
        """Update using profile object directly."""
        logger.info("Testing update of vector index using profile object directly...")
        temp_profile_name = "vector_ai_profile_temp"
        temp_profile = self.create_profile(profile_name=temp_profile_name)
        logger.info(f"Created temporary profile: {temp_profile_name}")
        try:
            self.vector_index.set_attribute("profile", temp_profile)
        except oracledb.NotSupportedError as e:
            logger.info(f"Expected NotSupportedError caught: {e}")
        except Exception as e:
            raise AssertionError(f"Unexpected exception: {e}")
        attrs = self.vector_index.get_attributes()
        assert attrs.profile_name in [self.profile.profile_name, temp_profile_name]
        logger.info(f"Attributes after attempted profile object update: {attrs.__dict__}")
        try:
            self.delete_profile(temp_profile)
            logger.info(f"Temporary profile '{temp_profile_name}' deleted successfully.")
        except Exception as e:
            logger.warning(f"Profile cleanup failed: {e}")

    def test_5225(self):
        """Update with invalid attribute name."""
        logger.info("Testing update with invalid attribute name...")
        with pytest.raises(oracledb.DatabaseError):
            self.vector_index.set_attribute("invalid_attr", "value")
        logger.info("Invalid attribute name correctly raised DatabaseError.")

    def test_5226(self):
        """Update with invalid type for integer field."""
        logger.info("Testing update with invalid type for integer field...")
        with pytest.raises(oracledb.DatabaseError):
            self.vector_index.set_attribute("chunk_size", "not_an_int")
        logger.info("Invalid integer type correctly raised DatabaseError.")

    def test_5227(self):
        """Update with invalid type for float field."""
        logger.info("Testing update with invalid type for float field...")
        with pytest.raises(oracledb.DatabaseError):
            self.vector_index.set_attribute("similarity_threshold", "NaN")
        logger.info("Invalid float type correctly raised DatabaseError.")

    def test_5228(self):
        """Update with invalid enum value for vector_distance_metric."""
        logger.info("Testing update with invalid enum value for vector_distance_metric...")
        with pytest.raises(oracledb.DatabaseError):
            self.vector_index.set_attribute("vector_distance_metric", "INVALID")
        logger.info("Invalid enum value correctly raised DatabaseError.")

    def test_5229(self):
        """Update on nonexistent vector index."""
        logger.info("Testing update on nonexistent vector index...")
        temp_index = VectorIndex(index_name="does_not_exist")
        with pytest.raises(AttributeError):
            temp_index.set_attribute("chunk_size", 512)
        logger.info("Nonexistent index update correctly raised AttributeError.")

    def test_5230(self):
        """Update with None as attribute name (should fail)."""
        logger.info("Testing update with None as attribute name...")
        with pytest.raises(TypeError):
            self.vector_index.set_attribute(None, 128)
        logger.info("None attribute name correctly raised TypeError.")

    def test_5231(self):
        """Update with None as attribute name for second time."""
        logger.info("Testing update with None as attribute name for second time...")
        with pytest.raises(TypeError):
            self.vector_index.set_attribute(None, 128)
        logger.info("None attribute name correctly raised TypeError.")

    def test_5232(self):
        """Update with invalid attributes object (non-object input)."""
        logger.info("Testing update with invalid attributes object (non-object input)...")
        with pytest.raises(AttributeError):
            self.vector_index.set_attributes(attributes="not_an_object")
        logger.info("Invalid attributes object correctly raised AttributeError.")

    def test_5233(self):
        """Update after disconnecting from the database."""
        logger.info("Testing update after disconnecting from the database...")
        select_ai.disconnect()
        with pytest.raises(DatabaseNotConnectedError):
            self.vector_index.set_attribute("chunk_size", 256)
        logger.info("DatabaseNotConnectedError correctly raised after disconnect.")
        logger.info("Reconnecting for further tests...")
        connect_kwargs = {
            "user": self.user,
            "password": self.password,
            "dsn": self.dsn,
        }
        wallet_location = os.environ.get("PYSAI_TEST_WALLET_LOCATION")
        wallet_password = os.environ.get("PYSAI_TEST_WALLET_PASSWORD")
        if wallet_location:
            connect_kwargs["config_dir"] = wallet_location
            connect_kwargs["wallet_location"] = wallet_location
        if wallet_password:
            connect_kwargs["wallet_password"] = wallet_password
        select_ai.connect(**connect_kwargs)
        assert select_ai.is_connected(), "Connection to DB failed"
        logger.info("Reconnection successful.")

    def test_5234(self):
        """Update with None as attribute value (should fail)."""
        logger.info("Testing update with None as attribute value...")
        with pytest.raises(oracledb.DatabaseError):
            self.vector_index.set_attribute("chunk_size", None)
        logger.info("None value correctly raised DatabaseError.")

    def test_5235(self):
        """Concurrent updates on the same vector index."""
        logger.info("Testing concurrent updates on the same vector index...")
        vecidx = VectorIndex()
        index1 = (list(vecidx.list(index_name_pattern=self.index_name)))[0]
        index2 = (list(vecidx.list(index_name_pattern=self.index_name)))[0]
        index1.set_attribute("match_limit", 15)
        index2.set_attribute("match_limit", 20)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Final match_limit value after concurrent updates: {attrs.match_limit}")
        assert attrs.match_limit in [15, 20]
        logger.info("Concurrent update behavior verified (last writer wins).")

    def test_5236(self):
        """Update with excessively large attribute value."""
        logger.info("Testing update with excessively large attribute value...")
        long_name = "X" * 500
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            self.vector_index.set_attribute("profile_name", long_name)
        assert "ORA-20048" in str(exc_info.value)
        logger.info("Large attribute value correctly raised DatabaseError.")

    def test_5237(self):
        """Repeated updates to match_limit (last writer wins)."""
        logger.info("Testing repeated updates to match_limit...")
        for i in range(5):
            self.vector_index.set_attribute("match_limit", i * 10)
            logger.info(f"Set match_limit to {i * 10}")
        attrs = self.vector_index.get_attributes()
        assert attrs.match_limit == 40
        logger.info("Repeated update test passed; last value retained.")

    def test_5238(self):
        """Update attribute after delete and recreate of vector index."""
        logger.info("Testing attribute update after deleting and recreating the vector index...")
        self.vector_index.delete(force=True)
        logger.info("Vector index deleted.")
        self.vector_index = VectorIndex(
            index_name=self.index_name,
            attributes=self.vector_index_attributes,
            description="Test vector index",
            profile=self.profile,
        )
        self.vector_index.create(replace=True)
        logger.info("Vector index recreated.")
        self.vector_index.set_attribute("match_limit", 10)
        attrs = self.vector_index.get_attributes()
        assert attrs.match_limit == 10
        logger.info("Update after recreation verified successfully.")

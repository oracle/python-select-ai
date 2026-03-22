# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------


import logging
import pytest
import select_ai
import test_env
import oracledb
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
def set_vec_params(request):
    params = {
        "user":                test_env.get_test_user(),
        "password":            test_env.get_test_password(),
        "dsn":                 test_env.get_connect_string(),
        "use_wallet":          test_env.get_use_wallet(),
        "user_ocid":           test_env.get_user_ocid(),
        "tenancy_ocid":        test_env.get_tenancy_ocid(),
        "private_key":         test_env.get_private_key(),
        "fingerprint":         test_env.get_fingerprint(),
        "cred_username":       test_env.get_cred_username(),
        "cred_password":       test_env.get_cred_password(),
        "oci_compartment_id":  test_env.get_compartment_id(),
        "embedding_location":  test_env.get_embedding_location(),
    }
    request.cls.set_vec_params = params

@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown(request, set_vec_params):
    logger.info("=== Setting up TestSetVectorIndexAttributes class ===")
    p = request.cls.set_vec_params
    test_env.create_connection(use_wallet=p["use_wallet"])
    assert select_ai.is_connected(), "Connection to DB failed"
    request.cls.user = p["user"]
    request.cls.password = p["password"]
    request.cls.dsn = p["dsn"]
    request.cls.use_wallet = p["use_wallet"]
    request.cls.user_ocid = p["user_ocid"]
    request.cls.tenancy_ocid = p["tenancy_ocid"]
    request.cls.private_key = p["private_key"]
    request.cls.fingerprint = p["fingerprint"]
    request.cls.cred_username = p["cred_username"]
    request.cls.cred_password = p["cred_password"]
    request.cls.oci_compartment_id = p["oci_compartment_id"]
    request.cls.embedding_location = p["embedding_location"]
    request.cls.objstore_cred      = "OBJSTORE_CRED"

    def get_native_cred_param(cred_name=None):
        logger.info(f"Preparing native credential params for: {cred_name}")
        return dict(
            credential_name = cred_name,
            user_ocid       = p["user_ocid"],
            tenancy_ocid    = p["tenancy_ocid"],
            private_key     = p["private_key"],
            fingerprint     = p["fingerprint"]
        )
    def get_cred_param(cred_name=None):
        logger.info(f"Preparing basic credential params for: {cred_name}")
        return dict(
            credential_name = cred_name,
            username        = p["cred_username"],
            password        = p["cred_password"]
        )
    request.cls.get_native_cred_param = staticmethod(get_native_cred_param)
    request.cls.get_cred_param = staticmethod(get_cred_param)
    request.cls.create_profile = staticmethod(lambda profile_name="vector_ai_profile": select_ai.Profile(
        profile_name=profile_name,
        attributes=select_ai.ProfileAttributes(
            credential_name="GENAI_CRED",
            provider=select_ai.OCIGenAIProvider(
                oci_compartment_id=p["oci_compartment_id"],
                oci_apiformat="GENERIC"
            )
        ),
        description="OCI GENAI Profile",
        replace=True
    ))
    request.cls.delete_profile = staticmethod(lambda profile: profile.delete())

    logger.info("Creating credentials: GENAI_CRED, OBJSTORE_CRED")
    genai_credential = get_native_cred_param("GENAI_CRED")
    objstore_credential = get_cred_param("OBJSTORE_CRED")
    select_ai.create_credential(credential=genai_credential, replace=True)
    select_ai.create_credential(credential=objstore_credential, replace=True)
    logger.info("Credentials created.")

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
    created_indexes = [idx.index_name for idx in VectorIndex.list()]
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
    try:
        select_ai.delete_credential("GENAI_CRED", force=True)
    except Exception as e:
        logger.warning(f"delete_credential() raised {e} unexpectedly.")
    try:
        select_ai.delete_credential("OBJSTORE_CRED", force=True)
    except Exception as e:
        logger.warning(f"delete_credential() raised {e} unexpectedly.")
    try:
        select_ai.disconnect()
    except Exception as e:
        logger.warning(f"Warning: disconnect failed ({e})")

@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info(f"--- Starting test: {request.function.__name__} ---")
    yield
    logger.info(f"--- Finished test: {request.function.__name__} ---")

@pytest.mark.usefixtures("set_vec_params", "setup_and_teardown")
class TestSetVectorIndexAttributes:
    def setup_method(self, method):
        logger.info(f"SetUp for {method.__name__}")
        vecidx = VectorIndex()
        self.vector_index = (list(vecidx.list(index_name_pattern=self.index_name)))[0]

    def teardown_method(self, method):
        logger.info(f"TearDown for {method.__name__}")

    def test_5201(self):
        """Update 'match_limit' attribute."""
        logger.info("Testing update of 'match_limit' attribute...")
        self.vector_index.set_attributes("match_limit", 10)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Updated match_limit: {attrs.match_limit}")
        assert attrs.match_limit == 10
        logger.info("Match limit update verified successfully.")

    def test_5202(self):
        """Update 'similarity_threshold' attribute."""
        logger.info("Testing update of 'similarity_threshold' attribute...")
        self.vector_index.set_attributes("similarity_threshold", 0.8)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Updated similarity_threshold: {attrs.similarity_threshold}")
        assert attrs.similarity_threshold == 0.8
        logger.info("Similarity threshold update verified successfully.")

    def test_5203(self):
        """Update multiple attributes with VectorIndexAttributes object."""
        logger.info("Testing update of multiple attributes via VectorIndexAttributes object...")
        update_attrs = VectorIndexAttributes(
            match_limit=5,
            similarity_threshold=0.5,
            location=self.embedding_location,
            refresh_rate=40
        )
        self.vector_index.set_attributes(attributes=update_attrs)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Updated attributes: {attrs.__dict__}")
        assert attrs.match_limit == 5
        assert attrs.similarity_threshold == 0.5
        assert attrs.location == self.embedding_location
        assert attrs.refresh_rate == 40
        logger.info("Multiple attributes update verified successfully.")

    def test_5204(self):
        """Repeated update of the same attribute 'similarity_threshold'."""
        logger.info("Testing repeated update of the same attribute 'similarity_threshold'...")
        self.vector_index.set_attributes("similarity_threshold", 0.8)
        self.vector_index.set_attributes("similarity_threshold", 0.5)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Final similarity_threshold value: {attrs.similarity_threshold}")
        assert attrs.similarity_threshold == 0.5
        logger.info("Repeated attribute update verified successfully.")

    def test_5205(self):
        """Update 'match_limit' with maximum allowed value."""
        logger.info("Testing update of 'match_limit' with maximum allowed value...")
        max_limit = 8192
        self.vector_index.set_attributes("match_limit", max_limit)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Set match_limit to: {attrs.match_limit}")
        assert attrs.match_limit == max_limit
        logger.info("Max value for match_limit verified successfully.")

    def test_5206(self):
        """Update match_limit with minimum value."""
        logger.info("Testing update of match_limit with minimum value...")
        min_limit = 1
        self.vector_index.set_attributes("match_limit", min_limit)
        logger.info(f"Set match_limit to {min_limit}, fetching attributes for verification...")
        attrs = self.vector_index.get_attributes()
        assert attrs.match_limit == min_limit
        logger.info("match_limit minimum value update verified successfully.")

    def test_5207(self):
        """Update match_limit with zero value."""
        logger.info("Testing update of match_limit with zero value...")
        min_limit = 0
        self.vector_index.set_attributes("match_limit", min_limit)
        logger.info("Fetching attributes to verify zero value update...")
        attrs = self.vector_index.get_attributes()
        assert attrs.match_limit == min_limit
        logger.info("match_limit zero value update verified successfully.")

    def test_5208(self):
        """Update profile_name with temporary profile."""
        temp_profile_name = "vector_ai_profile_temp"
        temp_profile = self.create_profile(profile_name=temp_profile_name)
        logger.info(f"Temporary profile created: {temp_profile_name}")
        self.vector_index.set_attributes("profile_name", temp_profile_name)
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
        self.vector_index.set_attributes("profile_name", self.profile.profile_name)
        attrs = self.vector_index.get_attributes()
        logger.info("VectorIndex reset to default profile, verifying...")
        assert attrs.profile_name == self.profile.profile_name
        logger.info("VectorIndex profile reset verified successfully.")

    def test_5209(self):
        """Update profile_name and then delete profile scenario."""
        logger.info("Testing update of profile_name followed by delete scenario...")
        temp_profile_name = "vector_ai_profile_temp"
        temp_profile = self.create_profile(profile_name=temp_profile_name)
        logger.info(f"Temporary profile created: {temp_profile_name}")
        self.vector_index.set_attributes("profile_name", temp_profile_name)
        logger.info(f"Set profile_name to {temp_profile_name}, verifying update...")
        attrs = self.vector_index.get_attributes()
        assert attrs.profile_name == temp_profile_name
        vecidx = VectorIndex()
        vec_index = (list(vecidx.list(index_name_pattern=self.index_name)))[0]
        logger.info(f"Persisted VectorIndex after profile update: {vec_index.__dict__}")
        assert attrs.profile_name == vec_index.profile.profile_name
        self.delete_profile(temp_profile)
        logger.info(f"Temporary profile deleted: {temp_profile_name}")
        logger.info("Verifying VectorIndex profile cleared after delete...")
        vecidx = VectorIndex()
        vec_index = (list(vecidx.list(index_name_pattern=self.index_name)))[0]
        attrs = vec_index.get_attributes()
        assert attrs.profile_name is None
        logger.info("Profile cleared successfully after deletion.")
        self.vector_index.set_attributes("profile_name", self.profile.profile_name)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Reset VectorIndex profile to default: {attrs.__dict__}")
        assert attrs.profile_name == self.profile.profile_name
        logger.info("Profile reset after delete verified successfully.")

    def test_5210(self):
        """Update refresh_rate attribute."""
        logger.info("Testing update of refresh_rate attribute...")
        self.vector_index.set_attributes("refresh_rate", 30)
        attrs = self.vector_index.get_attributes()
        assert attrs.refresh_rate == 30

    def test_5211(self):
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
        self.vector_index.set_attributes("object_storage_credential_name", "TEMP_OBJSTORE_CRED")
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
        self.vector_index.set_attributes("object_storage_credential_name", "OBJSTORE_CRED")
        logger.info(f"Restarting pipeline: {pipeline_name}")
        with select_ai.cursor() as cursor:
            cursor.execute("BEGIN dbms_cloud_pipeline.start_pipeline(pipeline_name => :1); END;", [pipeline_name])
        logger.info(f"Pipeline '{pipeline_name}' restarted successfully.")
        attrs = self.vector_index.get_attributes()
        assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
        logger.info("Object Store credential restored successfully.")

    def test_5212(self):
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
        self.vector_index.set_attributes("object_storage_credential_name", "TEMP_OBJSTORE_CRED")
        attrs = self.vector_index.get_attributes()
        assert attrs.object_storage_credential_name == "TEMP_OBJSTORE_CRED"
        logger.info(f"Credential updated to: {attrs.object_storage_credential_name}")
        logger.info("Deleting temporary credential: TEMP_OBJSTORE_CRED")
        try:
            select_ai.delete_credential("TEMP_OBJSTORE_CRED", force=True)
            logger.info("TEMP_OBJSTORE_CRED deleted successfully.")
        except Exception as e:
            pytest.fail(f"delete_credential() raised unexpected exception: {e}")
        logger.info("Verifying that VectorIndex no longer holds deleted credential...")
        vecidx = VectorIndex()
        vec_index = (list(vecidx.list(index_name_pattern=self.index_name)))[0]
        attrs = vec_index.get_attributes()
        assert attrs.object_storage_credential_name is None
        logger.info("Credential removal reflected in VectorIndex attributes.")
        logger.info("Restoring original Object Store credential: OBJSTORE_CRED")
        self.vector_index.set_attributes("object_storage_credential_name", "OBJSTORE_CRED")
        logger.info(f"Restarting pipeline: {pipeline_name}")
        with select_ai.cursor() as cursor:
            cursor.execute("BEGIN dbms_cloud_pipeline.start_pipeline(pipeline_name => :1); END;", [pipeline_name])
        logger.info(f"Pipeline '{pipeline_name}' restarted successfully.")
        attrs = self.vector_index.get_attributes()
        assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
        logger.info("Object Store credential restoration after delete verified successfully.")

    def test_5213(self):
        """Update multiple attributes together."""
        logger.info("Testing update of multiple attributes together...")
        updates = {
            "refresh_rate": 50,
            "similarity_threshold": 0.8,
            "match_limit": 10
        }
        for field, value in updates.items():
            logger.info(f"Updating {field} to {value}...")
            self.vector_index.set_attributes(field, value)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Fetched attributes after updates: {attrs.__dict__}")
        assert attrs.refresh_rate == updates["refresh_rate"]
        assert attrs.similarity_threshold == updates["similarity_threshold"]
        assert attrs.match_limit == updates["match_limit"]
        logger.info("All multiple attribute updates verified successfully.")

    def test_5214(self):
        """Update description (should raise DatabaseError)."""
        logger.info("Testing update of description attribute (should raise DatabaseError)...")
        with pytest.raises(oracledb.DatabaseError) as cm:
            self.vector_index.set_attributes("description", "updated description")
        assert "ORA-20048" in str(cm.value)
        logger.info("DatabaseError correctly raised for invalid description update.")

    def test_5215(self):
        """Update pipeline_name (should raise DatabaseError)."""
        logger.info("Testing update of pipeline_name (expected DatabaseError)...")
        with pytest.raises(oracledb.DatabaseError) as cm:
            self.vector_index.set_attributes("pipeline_name", "test_pipeline")
        assert "ORA-20048" in str(cm.value)
        attrs = self.vector_index.get_attributes()
        assert attrs.pipeline_name == "TEST_VECTOR_INDEX_ATTR$VECPIPELINE"
        logger.info("Pipeline update correctly raised error and original value retained.")

    def test_5216(self):
        """Update chunk_size (should fail)."""
        logger.info("Testing update of chunk_size (should fail with ORA-20047)...")
        attrs = self.vector_index.get_attributes()
        logger.info(f"Current attributes: {attrs.__dict__}")
        with pytest.raises(oracledb.DatabaseError) as cm:
            self.vector_index.set_attributes("chunk_size", 2048)
        assert "ORA-20047" in str(cm.value)
        attrs = self.vector_index.get_attributes()
        assert attrs.chunk_size == 1024
        logger.info("chunk_size update prevented successfully; original value verified.")

    def test_5217(self):
        """Update chunk_overlap (should fail)."""
        logger.info("Testing update of chunk_overlap (should fail with ORA-20047)...")
        with pytest.raises(oracledb.DatabaseError) as cm:
            self.vector_index.set_attributes("chunk_overlap", 256)
        assert "ORA-20047" in str(cm.value)
        attrs = self.vector_index.get_attributes()
        assert attrs.chunk_overlap == 128
        logger.info("chunk_overlap update prevented successfully; original value verified.")

    def test_5218(self):
        """Update vector_distance_metric (should fail)."""
        logger.info("Testing update of vector_distance_metric (should fail with ORA-20047)...")
        with pytest.raises(oracledb.DatabaseError) as cm:
            self.vector_index.set_attributes("vector_distance_metric", "EUCLIDEAN")
        assert "ORA-20047" in str(cm.value)
        attrs = self.vector_index.get_attributes()
        assert attrs.vector_distance_metric == "COSINE"
        logger.info("vector_distance_metric update prevented successfully.")

    def test_5219(self):
        """Partial update with VectorIndexAttributes object."""
        logger.info("Testing partial update with VectorIndexAttributes object...")
        update_attrs = VectorIndexAttributes(match_limit=20, chunk_size=2048)
        self.vector_index.set_attributes(attributes=update_attrs)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Attributes after update attempt: {attrs.__dict__}")
        assert attrs.match_limit == 20
        assert attrs.chunk_size == 1024
        logger.info("Partial update applied correctly; restricted fields unchanged.")

    def test_5220(self):
        """Update with invalid attribute combinations."""
        logger.info("Testing update with invalid attribute combinations...")
        update_attrs = VectorIndexAttributes(chunk_size=2048, chunk_overlap=256)
        self.vector_index.set_attributes(attributes=update_attrs)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Attributes after invalid update: {attrs.__dict__}")
        assert attrs.chunk_overlap == 128
        assert attrs.chunk_size == 1024
        logger.info("Invalid updates ignored; original attribute values retained.")

    def test_5221(self):
        """Update location (should raise ORA-20047)."""
        logger.info("Testing update of location (expected ORA-20047)...")
        with pytest.raises(oracledb.DatabaseError) as cm:
            self.vector_index.set_attributes("location", self.embedding_location)
        assert "ORA-20047" in str(cm.value)
        attrs = self.vector_index.get_attributes()
        assert attrs.location == self.embedding_location
        logger.info("Location update prevented successfully.")

    def test_5222(self):
        """Update using profile object directly."""
        logger.info("Testing update of vector index using profile object directly...")
        temp_profile_name = "vector_ai_profile_temp"
        temp_profile = self.create_profile(profile_name=temp_profile_name)
        logger.info(f"Created temporary profile: {temp_profile_name}")
        try:
            self.vector_index.set_attributes("profile", temp_profile)
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

    def test_5223(self):
        """Update with invalid attribute name."""
        logger.info("Testing update with invalid attribute name...")
        with pytest.raises(oracledb.DatabaseError):
            self.vector_index.set_attributes("invalid_attr", "value")
        logger.info("Invalid attribute name correctly raised DatabaseError.")

    def test_5224(self):
        """Update with invalid type for integer field."""
        logger.info("Testing update with invalid type for integer field...")
        with pytest.raises(oracledb.DatabaseError):
            self.vector_index.set_attributes("chunk_size", "not_an_int")
        logger.info("Invalid integer type correctly raised DatabaseError.")

    def test_5225(self):
        """Update with invalid type for float field."""
        logger.info("Testing update with invalid type for float field...")
        with pytest.raises(oracledb.DatabaseError):
            self.vector_index.set_attributes("similarity_threshold", "NaN")
        logger.info("Invalid float type correctly raised DatabaseError.")

    def test_5226(self):
        """Update with invalid enum value for vector_distance_metric."""
        logger.info("Testing update with invalid enum value for vector_distance_metric...")
        with pytest.raises(oracledb.DatabaseError):
            self.vector_index.set_attributes("vector_distance_metric", "INVALID")
        logger.info("Invalid enum value correctly raised DatabaseError.")

    def test_5227(self):
        """Update on nonexistent vector index."""
        logger.info("Testing update on nonexistent vector index...")
        temp_index = VectorIndex(index_name="does_not_exist")
        with pytest.raises(AttributeError):
            temp_index.set_attributes("chunk_size", 512)
        logger.info("Nonexistent index update correctly raised AttributeError.")

    def test_5228(self):
        """Update with None as attribute name (should fail)."""
        logger.info("Testing update with None as attribute name...")
        with pytest.raises(TypeError):
            self.vector_index.set_attributes(None, 128)
        logger.info("None attribute name correctly raised TypeError.")

    def test_5229(self):
        """Update with None as attribute name for second time."""
        logger.info("Testing update with None as attribute name for second time...")
        with pytest.raises(TypeError):
            self.vector_index.set_attributes(None, 128)
        logger.info("None attribute name correctly raised TypeError.")

    def test_5230(self):
        """Update with invalid attributes object (non-object input)."""
        logger.info("Testing update with invalid attributes object (non-object input)...")
        with pytest.raises(AttributeError):
            self.vector_index.set_attributes(attributes="not_an_object")
        logger.info("Invalid attributes object correctly raised AttributeError.")

    def test_5231(self):
        """Update after disconnecting from the database."""
        logger.info("Testing update after disconnecting from the database...")
        select_ai.disconnect()
        with pytest.raises(DatabaseNotConnectedError):
            self.vector_index.set_attributes("chunk_size", 256)
        logger.info("DatabaseNotConnectedError correctly raised after disconnect.")
        logger.info("Reconnecting for further tests...")
        test_env.create_connection(use_wallet=self.use_wallet)
        assert select_ai.is_connected(), "Connection to DB failed"
        logger.info("Reconnection successful.")

    def test_5232(self):
        """Update with None as attribute value (should fail)."""
        logger.info("Testing update with None as attribute value...")
        with pytest.raises(oracledb.DatabaseError):
            self.vector_index.set_attributes("chunk_size", None)
        logger.info("None value correctly raised DatabaseError.")

    def test_5233(self):
        """Concurrent updates on the same vector index."""
        logger.info("Testing concurrent updates on the same vector index...")
        vecidx = VectorIndex()
        index1 = (list(vecidx.list(index_name_pattern=self.index_name)))[0]
        index2 = (list(vecidx.list(index_name_pattern=self.index_name)))[0]
        index1.set_attributes("match_limit", 15)
        index2.set_attributes("match_limit", 20)
        attrs = self.vector_index.get_attributes()
        logger.info(f"Final match_limit value after concurrent updates: {attrs.match_limit}")
        assert attrs.match_limit in [15, 20]
        logger.info("Concurrent update behavior verified (last writer wins).")

    def test_5234(self):
        """Update with excessively large attribute value."""
        logger.info("Testing update with excessively large attribute value...")
        long_name = "X" * 500
        with pytest.raises(oracledb.DatabaseError) as cm:
            self.vector_index.set_attributes("profile_name", long_name)
        assert "ORA-20048" in str(cm.value)
        logger.info("Large attribute value correctly raised DatabaseError.")

    def test_5235(self):
        """Repeated updates to match_limit (last writer wins)."""
        logger.info("Testing repeated updates to match_limit...")
        for i in range(5):
            self.vector_index.set_attributes("match_limit", i * 10)
            logger.info(f"Set match_limit to {i * 10}")
        attrs = self.vector_index.get_attributes()
        assert attrs.match_limit == 40
        logger.info("Repeated update test passed; last value retained.")

    def test_5236(self):
        """Update attribute after delete and recreate of vector index."""
        logger.info("Testing attribute update after deleting and recreating the vector index...")
        self.vector_index.delete(force=True)
        logger.info("Vector index deleted.")
        self.vector_index.create(replace=True)
        logger.info("Vector index recreated.")
        self.vector_index.set_attributes("match_limit", 10)
        attrs = self.vector_index.get_attributes()
        assert attrs.match_limit == 10
        logger.info("Update after recreation verified successfully.")

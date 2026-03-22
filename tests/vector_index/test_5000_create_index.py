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
from select_ai import OracleVectorIndexAttributes

logger = logging.getLogger("TestCreateVectorIndex")

@pytest.fixture(scope="class", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO
    )

@pytest.fixture(scope="class")
def vector_index_params(request):
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
    request.cls.vector_index_params = params

@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown(request, vector_index_params):
    logger.info("\n=== Setting up TestCreateVectorIndex class ===")
    test_env.create_connection(use_wallet=request.cls.vector_index_params["use_wallet"])
    assert select_ai.is_connected(), "Connection to DB failed"
    logger.info("Fetching credential secrets and OCI configuration...")
    # Create credentials and profile
    request.cls.create_credential()
    request.cls.profile = request.cls.create_profile()
    logger.info("Setup complete.\n")
    yield

    logger.info("\n=== Tearing down TestCreateVectorIndex class ===")
    request.cls.delete_profile(request.cls.profile)
    request.cls.delete_credential()
    logger.info("Disconnecting from DB...")
    try:
        select_ai.disconnect()
    except Exception as e:
        logger.warning(f"Warning: disconnect failed ({e})")

@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info(f"--- Starting test: {request.function.__name__} ---")
    yield
    logger.info(f"--- Finished test: {request.function.__name__} ---")

@pytest.mark.usefixtures("vector_index_params", "setup_and_teardown")
class TestCreateVectorIndex:

    @classmethod
    def get_native_cred_param(cls, cred_name=None) -> dict:
        logger.info(f"Preparing native credential params for: {cred_name}")
        params = cls.vector_index_params
        return dict(
            credential_name = cred_name,
            user_ocid       = params["user_ocid"],
            tenancy_ocid    = params["tenancy_ocid"],
            private_key     = params["private_key"],
            fingerprint     = params["fingerprint"]
        )

    @classmethod
    def get_cred_param(cls, cred_name=None) -> dict:
        logger.info(f"Preparing basic credential params for: {cred_name}")
        params = cls.vector_index_params
        return dict(
            credential_name = cred_name,
            username        = params["cred_username"],
            password        = params["cred_password"]
        )
    @classmethod
    def create_credential(cls, genai_cred="GENAI_CRED", objstore_cred="OBJSTORE_CRED"):
        logger.info(f"Creating credentials: {genai_cred}, {objstore_cred}")
        genai_credential = cls.get_native_cred_param(genai_cred)
        objstore_credential = cls.get_cred_param(objstore_cred)
        try:
            logger.info(f"Creating GenAI credential: {genai_cred}")
            select_ai.create_credential(credential=genai_credential, replace=True)
            logger.info("GenAI credential created.")
        except Exception as e:
            raise AssertionError(f"create_credential() raised {e} unexpectedly.")
        try:
            logger.info(f"Creating ObjectStore credential: {objstore_cred}")
            select_ai.create_credential(credential=objstore_credential, replace=True)
            logger.info("ObjectStore credential created.")
        except Exception as e:
            raise AssertionError(f"create_credential() raised {e} unexpectedly.")

    @classmethod
    def create_profile(cls, profile_name="vector_ai_profile"):
        logger.info(f"Creating Profile: {profile_name}")
        params = cls.vector_index_params
        provider = select_ai.OCIGenAIProvider(
            oci_compartment_id=params["oci_compartment_id"],
            oci_apiformat="GENERIC"
        )
        profile_attributes = select_ai.ProfileAttributes(
            credential_name="GENAI_CRED",
            provider=provider
        )
        profile = select_ai.Profile(
            profile_name=profile_name,
            attributes=profile_attributes,
            description="OCI GENAI Profile",
            replace=True
        )
        logger.info(f"Profile '{profile_name}' created successfully.")
        return profile

    @classmethod
    def delete_profile(cls, profile):
        logger.info("Deleting profile...")
        try:
            profile.delete()
            logger.info(f"Profile '{profile.profile_name}' deleted successfully.")
        except Exception as e:
            raise AssertionError(f"profile.delete() raised {e} unexpectedly.")

    @classmethod
    def delete_credential(cls):
        logger.info("Deleting credentials...")
        try:
            select_ai.delete_credential("GENAI_CRED", force=True)
            logger.info("Deleted credential 'GENAI_CRED'")
        except Exception as e:
            logger.warning(f"delete_credential() raised {e} unexpectedly.")
        try:
            select_ai.delete_credential("OBJSTORE_CRED", force=True)
            logger.info("Deleted credential 'OBJSTORE_CRED'")
        except Exception as e:
            logger.warning(f"delete_credential() raised {e} unexpectedly.")

    def setup_method(self, method):
        logger.info(f"\n--- Starting test: {method.__name__} ---")
        self.objstore_cred = "OBJSTORE_CRED"
        params = self.vector_index_params
        self.vector_index_attributes = OracleVectorIndexAttributes(
            location=params["embedding_location"],
            object_storage_credential_name=self.objstore_cred
        )
        self.profile = self.profile
        self.vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            description="Test vector index",
            profile=self.profile
        )

    def teardown_method(self, method):
        logger.info(f"--- Finished test: {method.__name__} ---")
        try:
            vector_index = select_ai.VectorIndex(index_name="test_vector_index")
            vector_index.delete(force=True)
            logger.info("Vector index deleted successfully.")
        except Exception as e:
            logger.warning(f"Warning: vector index cleanup failed: {e}")

    def test_5001(self):
        """Test successful vector index creation."""
        try:
            self.vector_index.create(replace=True)
            logger.info("Vector index created successfully.")
        except Exception as e:
            pytest.fail(f"VectorIndex.create raised an unexpected exception: {e}")
        logger.info("Verifying created vector index...")
        vector_index = select_ai.VectorIndex()
        indexes = [i.index_name for i in vector_index.list()]
        logger.info(f"Indexes found: {indexes}")
        assert "TEST_VECTOR_INDEX" in indexes
        logger.info("Verified vector index creation successfully.")

    def test_5002(self):
        """Test vector index creation with replace=False."""
        try:
            self.vector_index.create(replace=False)
            logger.info("Vector index created successfully.")
        except Exception as e:
            pytest.fail(f"VectorIndex.create raised an unexpected exception: {e}")
        logger.info("Verifying created vector index...")
        vector_index = select_ai.VectorIndex()
        indexes = [i.index_name for i in vector_index.list()]
        logger.info(f"Indexes found: {indexes}")
        assert "TEST_VECTOR_INDEX" in indexes
        logger.info("Verified vector index presence.")

    def test_5003(self):
        """Test vector index creation with empty description."""
        params = self.vector_index_params
        vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            description="",
            profile=self.profile
        )
        try:
            vector_index.create(replace=True)
            logger.info("Vector index created successfully with empty description.")
        except Exception as e:
            pytest.fail(f"VectorIndex.create raised an unexpected exception: {e}")
        logger.info("Verifying created vector index...")
        vector_index = select_ai.VectorIndex()
        indexes = [i.index_name for i in vector_index.list()]
        logger.info(f"Indexes found: {indexes}")
        assert "TEST_VECTOR_INDEX" in indexes
        logger.info("Verified vector index creation with empty description.")

    def test_5004(self):
        """Test vector index recreation with replace=True."""
        try:
            self.vector_index.create(replace=True)
            logger.info("First creation successful.")
            self.vector_index.create(replace=True)
            logger.info("Second creation successful with replace=True.")
        except Exception as e:
            pytest.fail(f"VectorIndex.create raised an unexpected exception: {e}")

    def test_5005(self):
        """Test vector index recreation with replace=False (expect failure)."""
        try:
            self.vector_index.create(replace=False)
            logger.info("First creation successful.")
        except Exception as e:
            pytest.fail(f"Create vector index failed unexpectedly: {e}")
        with pytest.raises(oracledb.DatabaseError) as cm:
            self.vector_index.create(replace=False)
        logger.info(f"Expected DatabaseError raised: {cm.value}")
        assert "ORA-20048" in str(cm.value)
        assert "already exists" in str(cm.value)
        logger.info("Verified error on duplicate creation with replace=False.")

    def test_5006(self):
        """Test minimal attribute vector index creation."""
        params = self.vector_index_params
        vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            profile=self.profile
        )
        try:
            vector_index.create(replace=True)
            logger.info("Vector index created successfully with minimal attributes.")
        except Exception as e:
            pytest.fail(f"VectorIndex.create raised an unexpected exception: {e}")

    def test_5007(self):
        """Test vector index recreation after delete."""
        try:
            self.vector_index.create(replace=True)
            logger.info("Vector index created successfully.")
        except Exception as e:
            pytest.fail(f"VectorIndex.create raised an unexpected exception: {e}")
        logger.info("Deleting vector index...")
        vector_index = select_ai.VectorIndex(index_name="test_vector_index")
        vector_index.delete(force=True)
        logger.info("Vector index deleted successfully.")
        logger.info("Recreating vector index...")
        try:
            self.vector_index.create(replace=True)
            logger.info("Vector index recreated successfully.")
        except Exception as e:
            pytest.fail(f"VectorIndex.create raised an unexpected exception: {e}")

    def test_5008(self):
        """Test vector index creation with invalid credential."""
        params = self.vector_index_params
        vector_index_attributes = OracleVectorIndexAttributes(
            location=params["embedding_location"],
            object_storage_credential_name="invalidObjStore_cred"
        )
        vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.profile
        )
        with pytest.raises(oracledb.DatabaseError) as cm:
            vector_index.create(replace=True)
        logger.info(f"Expected DatabaseError raised: {cm.value}")

    def test_5009(self):
        """Test vector index creation with invalid location."""
        params = self.vector_index_params
        vector_index_attributes = OracleVectorIndexAttributes(
            location="invalid_location",
            object_storage_credential_name=self.objstore_cred
        )
        vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.profile
        )
        with pytest.raises(oracledb.DatabaseError) as cm:
            vector_index.create(replace=True)
        logger.info(f"Expected DatabaseError raised: {cm.value}")

    def test_5010(self):
        """Test vector index creation with missing attributes."""
        with pytest.raises(AttributeError):
            select_ai.VectorIndex(
                index_name="test_vector_index",
                attributes=None,
                profile=self.profile
            ).create()
        logger.info("Expected AttributeError raised for missing attributes.")

    def test_5011(self):
        """Test vector index creation with invalid attributes type."""
        with pytest.raises(TypeError):
            select_ai.VectorIndex(
                index_name="test_vector_index",
                attributes="invalid_attributes",
                profile=self.profile
            ).create()
        logger.info("Expected TypeError raised for invalid attribute type.")

    def test_5012(self):
        """Test vector index creation with invalid name type."""
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.VectorIndex(
                index_name=12345,
                attributes=self.vector_index_attributes,
                profile=self.profile
            ).create()
        assert "ORA-20048" in str(cm.value)
        assert "Invalid vector index name" in str(cm.value)
        logger.info(f"Expected DatabaseError raised: {cm.value}")

    def test_5013(self):
        """Test vector index creation with empty name."""
        with pytest.raises(oracledb.DatabaseError) as cm:
            select_ai.VectorIndex(
                index_name="",
                attributes=self.vector_index_attributes,
                profile=self.profile
            ).create()
        assert "ORA-20048" in str(cm.value)
        assert "Missing vector index name" in str(cm.value)
        logger.info(f"Expected DatabaseError raised: {cm.value}")

    def test_5014(self):
        """Test vector index creation with invalid profile."""
        with pytest.raises(TypeError) as cm:
            vector_index = select_ai.VectorIndex(
                index_name="test_vector_index",
                attributes=self.vector_index_attributes,
                description="Test vector index",
                profile="invalid_profile"
            )
            vector_index.create()
        logger.info(f"Expected ValueError raised for invalid profile: {cm.value}")

    def test_5015(self):
        """Test vector index creation with None attributes."""
        with pytest.raises(TypeError) as cm:
            vector_index = select_ai.VectorIndex(
                index_name="test_vector_index",
                attributes=None,
                description="Test vector index",
                profile="invalid_profile"
            )
            vector_index.create()
        logger.info(f"Expected TypeError raised for None attributes: {cm.value}")

    def test_5016(self):
        """Test vector index creation with long name (>128 chars)."""
        long_name = "X" * 150
        vector_index = select_ai.VectorIndex(
            index_name=long_name,
            attributes=self.vector_index_attributes,
            profile=self.profile
        )
        with pytest.raises(oracledb.DatabaseError) as cm:
            vector_index.create()
        logger.info(f"Expected DatabaseError raised for long name: {cm.value}")

    def test_5017(self):
        """Test vector index creation with long description."""
        long_desc = "D" * 5000
        vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            description=long_desc,
            profile=self.profile
        )
        with pytest.raises(oracledb.DatabaseError) as cm:
            vector_index.create(replace=True)
        assert "ORA-20045" in str(cm.value)
        assert "description is too long" in str(cm.value)
        logger.info(f"Expected DatabaseError raised: {cm.value}")

    def test_5018(self):
        """Test multiple recreations of vector index (10x)."""
        for _ in range(10):
            self.vector_index.create(replace=True)
        logger.info("Successfully recreated vector index multiple times.")

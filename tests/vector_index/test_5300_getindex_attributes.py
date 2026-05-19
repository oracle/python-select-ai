# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import logging
import pytest
import select_ai
from select_ai import VectorIndex, OracleVectorIndexAttributes
from select_ai.errors import VectorIndexNotFoundError

logger = logging.getLogger("TestGetVectorIndexAttributes")


@pytest.fixture(scope="class", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO
    )


@pytest.fixture(scope="class")
def vector_attr_params(
    request,
    vcidx_params,
):
    request.cls.vector_attr_params = vcidx_params


@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown(request, connect, vector_attr_params, test_env):
    logger.info("=== Setting up TestGetVectorIndexAttributes class ===")
    p = request.cls.vector_attr_params

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
    request.cls.reconnect_params = test_env.connect_params()

    logger.info("Fetching credential secrets and OCI configuration...")
    request.cls.create_credential()
    request.cls.profile = request.cls.create_profile()
    logger.info("Profile 'vector_ai_profile' created successfully.")

    # create vector index
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

    logger.info("=== Tearing down TestGetVectorIndexAttributes class ===")

    # Delete Vector Index
    try:
        vector_index = VectorIndex(index_name=request.cls.index_name)
        vector_index.delete(force=True)
    except Exception as e:
        logger.warning(f"drop vector index failed: {e}")

    # Delete Profile
    try:
        request.cls.profile.delete()
    except Exception as e:
        logger.warning(f"profile.delete() raised {e} unexpectedly.")

    # Delete Credential
    request.cls.delete_credential()


@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info(f"--- Starting test: {request.function.__name__} ---")
    yield
    logger.info(f"--- Finished test: {request.function.__name__} ---")


@pytest.mark.usefixtures("vector_attr_params", "setup_and_teardown")
class TestGetVectorIndexAttributes:
    @classmethod
    def get_native_cred_param(cls, cred_name=None):
        logger.info(f"Preparing native credential params for: {cred_name}")
        p = cls.vector_attr_params
        return dict(
            credential_name=cred_name,
            user_ocid=p["user_ocid"],
            tenancy_ocid=p["tenancy_ocid"],
            private_key=p["private_key"],
            fingerprint=p["fingerprint"]
        )

    @classmethod
    def get_cred_param(cls, cred_name=None):
        logger.info(f"Preparing basic credential params for: {cred_name}")
        p = cls.vector_attr_params
        return dict(
            credential_name=cred_name,
            username=p["cred_username"],
            password=p["cred_password"]
        )

    @classmethod
    def create_credential(cls, genai_cred="GENAI_CRED", objstore_cred="OBJSTORE_CRED"):
        logger.info("Creating credentials: GENAI_CRED, OBJSTORE_CRED")
        p = cls.vector_attr_params

        genai_credential = cls.get_native_cred_param(genai_cred)
        select_ai.create_credential(credential=genai_credential, replace=True)

        # Only create OBJSTORE_CRED if creds are provided in env
        if p.get("cred_username") and p.get("cred_password"):
            objstore_credential = cls.get_cred_param(objstore_cred)
            select_ai.create_credential(credential=objstore_credential, replace=True)
            logger.info("Credentials created.")
        else:
            logger.info("Skipping ObjectStore credential creation (CRED_USERNAME/CRED_PASSWORD not set).")

    @classmethod
    def create_profile(cls):
        p = cls.vector_attr_params
        provider = select_ai.OCIGenAIProvider(
            oci_compartment_id=p["oci_compartment_id"],
            oci_apiformat="GENERIC",
            embedding_model="cohere.embed-english-v3.0",
        )
        profile_attributes = select_ai.ProfileAttributes(
            credential_name="GENAI_CRED",
            provider=provider
        )
        return select_ai.Profile(
            profile_name="vector_ai_profile",
            attributes=profile_attributes,
            description="OCI GENAI Profile",
            replace=True
        )

    @classmethod
    def delete_credential(cls):
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
        logger.info(f"SetUp for {method.__name__}")
        vecidx = VectorIndex()
        self.vector_index = (list(vecidx.list(index_name_pattern=self.index_name)))[0]

    def teardown_method(self, method):
        logger.info(f"TearDown for {method.__name__}")

    # ----------------
    # Positive tests
    # ----------------
    def test_5301(self):
        """Get vector index attributes and verify type."""
        logger.info("Getting vector index attributes and verifying type...")
        attrs = self.vector_index.get_attributes()
        assert isinstance(attrs, OracleVectorIndexAttributes)
        logger.info("Attributes type verified successfully.")

    def test_5302(self):
        """Verify core values of vector index attributes."""
        logger.info("Getting vector index attributes and verifying core values...")
        attrs = self.vector_index.get_attributes()
        assert attrs.location == self.embedding_location
        assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
        assert attrs.profile_name == "vector_ai_profile"
        assert attrs.pipeline_name == f"{self.index_name.upper()}$VECPIPELINE"
        logger.info("Core attribute values verified successfully.")

    def test_5303(self):
        """Additional sanity checks on vector index attributes."""
        logger.info("Performing additional sanity checks on vector index attributes...")
        attrs = self.vector_index.get_attributes()
        assert attrs.chunk_size is None
        assert attrs.chunk_overlap is None
        assert attrs.match_limit is None
        assert attrs.refresh_rate == 1440
        assert attrs.vector_distance_metric is None
        assert attrs.vector_db_provider.value == "oracle"
        logger.info("Additional sanity checks passed successfully.")

    def test_5304(self):
        """Verify required fields in attributes object."""
        logger.info("Verifying attributes object contains required fields...")
        attrs = self.vector_index.get_attributes()
        logger.info(f"Attributes dict: {attrs.__dict__}")
        assert hasattr(attrs, "location")
        assert hasattr(attrs, "object_storage_credential_name")
        logger.info("Attributes contain all expected fields.")

    def test_5305(self):
        """Repeatability: fetch attributes twice and compare."""
        logger.info("Fetching attributes twice to confirm repeatability...")
        attrs1 = self.vector_index.get_attributes()
        attrs2 = self.vector_index.get_attributes()
        assert attrs1.location == attrs2.location
        logger.info("Attribute values are repeatable across calls.")

    def test_5306(self):
        """Test case-insensitive index name handling."""
        logger.info("Testing case-insensitive index name handling...")
        vecidx = VectorIndex()
        vector_index = (list(vecidx.list(index_name_pattern=self.index_name.lower())))[0]
        attrs = vector_index.get_attributes()
        assert attrs.location == self.embedding_location
        logger.info("Case-insensitive index name test passed.")

    def test_5307(self):
        """Type check on key vector index attributes."""
        logger.info("Performing type check on key vector index attributes...")
        attrs = self.vector_index.get_attributes()
        logger.info(f"{attrs}")
        assert isinstance(attrs.location, str)
        assert isinstance(attrs.profile_name, str)
        assert isinstance(attrs.object_storage_credential_name, str)
        logger.info("All attribute fields are of correct type.")

    # ----------------
    # Negative tests
    # ----------------
    def test_5308(self):
        """Calling get_attributes on nonexistent index raises error."""
        logger.info("Testing get_attributes() with a nonexistent index...")
        with pytest.raises(VectorIndexNotFoundError):
            VectorIndex(index_name="does_not_exist").get_attributes()
        logger.info("Nonexistent index correctly raised VectorIndexNotFoundError.")

    def test_5309(self):
        """verify error after deleting a temporary vector index."""
        logger.info("Testing error after deleting a temporary vector index...")
        vector_index_attributes = OracleVectorIndexAttributes(
            location=self.embedding_location,
            object_storage_credential_name="OBJSTORE_CRED"
        )
        logger.info("Creating temporary vector index...")
        temp_index = VectorIndex(
            index_name="temp_index_for_delete",
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.profile
        )
        temp_index.create(replace=True)
        logger.info("Temporary vector index created.")
        temp_index.delete(force=True)
        logger.info("Temporary vector index deleted. Attempting to fetch attributes...")
        with pytest.raises(VectorIndexNotFoundError):
            VectorIndex(index_name="temp_index_for_delete").get_attributes()
        logger.info("Expected error raised after deleting index.")

    def test_5310(self):
        """Access attributes after deleting the vector index (should use cache)."""
        logger.info("Testing access to attributes object after deleting the vector index...")
        vector_index_attributes = OracleVectorIndexAttributes(
            location=self.embedding_location,
            object_storage_credential_name="OBJSTORE_CRED"
        )
        logger.info("Creating temporary vector index for deletion test...")
        temp_index = VectorIndex(
            index_name="temp_index_for_delete",
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.profile
        )
        temp_index.create(replace=True)
        logger.info("Fetching attributes before deletion...")
        attrs = temp_index.get_attributes()
        assert isinstance(attrs, OracleVectorIndexAttributes)
        assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
        assert attrs.location == self.embedding_location
        logger.info("Deleting temporary index...")
        temp_index.delete(force=True)
        logger.info("Accessing cached attributes after deletion...")
        logger.info(f"After delete: {attrs}")
        assert isinstance(attrs, OracleVectorIndexAttributes)
        assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
        assert attrs.location == self.embedding_location
        logger.info("Attributes object remains valid after deletion.")

    def test_5311(self):
        """get_attributes with empty index name raises error."""
        logger.info("Testing get_attributes() with empty index name...")
        with pytest.raises(AttributeError):
            VectorIndex(index_name="").get_attributes()
        logger.info("Empty name correctly raised AttributeError.")

    def test_5312(self):
        """get_attributes with None as index name raises error."""
        logger.info("Testing get_attributes() with None as index name...")
        with pytest.raises(AttributeError):
            VectorIndex(index_name=None).get_attributes()
        logger.info("None name correctly raised AttributeError.")

    def test_5313(self):
        """get_attributes with special characters in index name."""
        logger.info("Testing get_attributes() with special characters in index name...")
        with pytest.raises(VectorIndexNotFoundError):
            VectorIndex(index_name='@@invalid!!').get_attributes()
        logger.info("Special character name correctly raised VectorIndexNotFoundError.")

    def test_5314(self):
        """get_attributes with Unicode index name raises error."""
        logger.info("Testing get_attributes() with Unicode index name...")
        with pytest.raises(VectorIndexNotFoundError):
            VectorIndex(index_name='テスト').get_attributes()
        logger.info("Unicode name correctly raised VectorIndexNotFoundError.")

    # ----------------
    # Stress / Edge cases
    # ----------------
    def test_5315(self):
        """Multiple indices: check their attribute differences."""
        logger.info("Creating multiple vector indices to compare their attributes...")
        vector_index_attributes = OracleVectorIndexAttributes(
            location=self.embedding_location,
            object_storage_credential_name="OBJSTORE_CRED"
        )
        logger.info("Creating index_a...")
        index_a = VectorIndex(
            index_name="index_a",
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.profile
        )
        index_a.create(replace=True)
        logger.info("Creating index_b...")
        index_b = VectorIndex(
            index_name="index_b",
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.profile
        )
        index_b.create(replace=True)
        logger.info("Fetching attributes for both indices...")
        attrs_a = VectorIndex(index_name="index_a").get_attributes()
        logger.info(f"Attrs_a: {attrs_a}")
        attrs_b = VectorIndex(index_name="index_b").get_attributes()
        assert attrs_a.pipeline_name != attrs_b.pipeline_name
        logger.info("Indices have distinct pipeline names as expected.")
        logger.info("Deleting both indices...")
        index_a.delete(force=True)
        index_b.delete(force=True)
        logger.info("Both indices deleted successfully.")

    def test_5316(self):
        """Attributes remain consistent after index delete and recreate."""
        logger.info("Testing attributes consistency after delete and recreate...")
        vector_index_attributes = OracleVectorIndexAttributes(
            location=self.embedding_location,
            object_storage_credential_name="OBJSTORE_CRED"
        )
        logger.info("Creating temporary vector index for recreate test...")
        temp_index = VectorIndex(
            index_name="temp_recreate",
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.profile
        )
        temp_index.create(replace=True)
        logger.info("Deleting temporary index...")
        temp_index.delete(force=True)
        logger.info("Recreating temporary index...")
        temp_index.create(replace=True)
        logger.info("Fetching attributes after recreation...")
        attrs = VectorIndex(index_name="temp_recreate").get_attributes()
        assert attrs.object_storage_credential_name == "OBJSTORE_CRED"
        temp_index.delete(force=True)
        logger.info("Recreate test completed successfully.")

    def test_5317(self):
        """get_attributes with very long index name raises error."""
        logger.info("Testing get_attributes() with very long index name...")
        long_name = "X" * 100
        with pytest.raises(VectorIndexNotFoundError):
            VectorIndex(index_name=long_name).get_attributes()
        logger.info("Long name correctly raised VectorIndexNotFoundError.")

    def test_5318(self):
        """get_attributes after disconnecting from database raises error."""
        logger.info("Testing get_attributes() after disconnecting from database...")
        select_ai.disconnect()
        with pytest.raises(Exception):
            VectorIndex(index_name=self.index_name).get_attributes()
        logger.info("Expected error raised after disconnect.")
        logger.info("Reconnecting for remaining tests...")

        select_ai.connect(**self.reconnect_params)

        logger.info("Reconnection successful.")

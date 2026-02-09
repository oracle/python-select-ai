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

logger = logging.getLogger("TestListVectorIndex")

@pytest.fixture(scope="class", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO
    )

@pytest.fixture(scope="class")
def list_vec_params(request):
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
    request.cls.list_vec_params = params

@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown(request, list_vec_params):
    logger.info("=== Setting up TestListVectorIndex class ===")
    p = request.cls.list_vec_params
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

    logger.info("Creating credentials: GENAI_CRED, OBJSTORE_CRED")
    genai_credential = get_native_cred_param("GENAI_CRED")
    objstore_credential = get_cred_param("OBJSTORE_CRED")
    select_ai.create_credential(credential=genai_credential, replace=True)
    select_ai.create_credential(credential=objstore_credential, replace=True)
    logger.info("Credentials created.")

    provider = select_ai.OCIGenAIProvider(
        oci_compartment_id=p["oci_compartment_id"],
        oci_apiformat="GENERIC"
    )
    profile_attributes = select_ai.ProfileAttributes(
        credential_name="GENAI_CRED",
        provider=provider
    )
    request.cls.profile = select_ai.Profile(
        profile_name="vector_ai_profile",
        attributes=profile_attributes,
        description="OCI GENAI Profile",
        replace=True
    )
    logger.info("Profile 'vector_ai_profile' created successfully.")

    def create_vector_index(index_name):
        logger.info(f"Creating vector index: {index_name}")
        vector_index_attributes = select_ai.OracleVectorIndexAttributes(
            location=p["embedding_location"],
            object_storage_credential_name="OBJSTORE_CRED"
        )
        vector_index = select_ai.VectorIndex(
            index_name=index_name,
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=request.cls.profile
        )
        vector_index.create(replace=True)
        logger.info(f"Vector index '{index_name}' created successfully.")

    request.cls.indexes = [f"test_vector_index{i}" for i in range(1, 6)] + \
        [f"test_vecidx{i}" for i in range(1, 3)]
    for idx in request.cls.indexes:
        try:
            create_vector_index(index_name=idx)
        except Exception as exc:
            logger.warning(f"Index creation failed or already exists for {idx}: {exc}")

    yield

    logger.info("=== Tearing down TestListVectorIndex class ===")
    for idx in request.cls.indexes:
        try:
            vector_index = select_ai.VectorIndex(index_name=idx)
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

@pytest.mark.usefixtures("list_vec_params", "setup_and_teardown")
class TestListVectorIndex:
    def setup_method(self, method):
        logger.info(f"SetUp for {method.__name__}")
        self.vector_index = select_ai.VectorIndex()

    def teardown_method(self, method):
        logger.info(f"TearDown for {method.__name__}")

    # ----------------
    # Positive tests
    # ----------------
    def test_5401(self):
        """Verify list of vector indexes with matching names."""
        logger.info("Verifying list of vector indexes with matching names...")
        expected_index_names = [f"TEST_VECTOR_INDEX{i}" for i in range(1, 6)] + \
                               [f"TEST_VECIDX{i}" for i in range(1, 3)]
        actual_indexes = list(self.vector_index.list(index_name_pattern=".*"))
        logger.info(f"Found {len(actual_indexes)} indexes, verifying names match expectations...")
        assert len(actual_indexes) == len(expected_index_names), \
            f"Expected {len(expected_index_names)} indexes, got {len(actual_indexes)}"
        actual_index_names = [idx.index_name for idx in actual_indexes]
        assert sorted(actual_index_names) == sorted(expected_index_names), \
            f"Expected names {sorted(expected_index_names)}, got {sorted(actual_index_names)}"
        logger.info("All index names matched as expected.")

    def test_5402(self):
        """Verify each index has correct profile name."""
        logger.info("Verifying each index has correct profile name...")
        expected_profile = "vector_ai_profile"
        for index in self.vector_index.list(index_name_pattern=".*"):
            assert index.profile.profile_name == expected_profile, \
                f"Profile mismatch for {index.index_name}: expected {expected_profile}, got {index.profile.profile_name}"
        logger.info("All indexes have correct profile name.")

    def test_5403(self):
        """Verify each index has correct object store credential name."""
        logger.info("Verifying each index has correct object store credential name...")
        expected_credential = "OBJSTORE_CRED"
        for index in self.vector_index.list(index_name_pattern=".*"):
            assert index.attributes.object_storage_credential_name == expected_credential, \
                f"Credential mismatch for {index.index_name}: expected {expected_credential}, got {index.attributes.object_storage_credential_name}"
        logger.info("All indexes have correct object store credential name.")

    def test_5404(self):
        """Verify descriptions for all indexes."""
        logger.info("Verifying descriptions for all indexes...")
        expected_description = "Test vector index"
        for index in self.vector_index.list(index_name_pattern=".*"):
            assert index.description == expected_description, \
                f"Description mismatch for {index.index_name}: expected {expected_description}, got {index.description}"
        logger.info("All indexes have correct descriptions.")

    def test_5405(self):
        """Test exact match listing for index name."""
        logger.info("Testing exact match listing for index name 'test_vector_index1'...")
        indexes = self.vector_index.list(index_name_pattern="^test_vector_index1$")
        assert list(indexes)[0].index_name == "TEST_VECTOR_INDEX1"
        logger.info("Exact match returned correct index.")

    def test_5406(self):
        """Verify multiple matches for pattern."""
        logger.info("Verifying multiple matches for pattern '^test_vector_index'...")
        actual_indexes = list(self.vector_index.list(index_name_pattern="^test_vector_index"))
        expected_count = 5
        assert len(actual_indexes) == expected_count, \
            f"Expected {expected_count} indexes, got {len(actual_indexes)}"
        actual_index_names = [index.index_name for index in actual_indexes]
        expected_index_names = [f"TEST_VECTOR_INDEX{i}" for i in range(1, 6)]
        assert sorted(actual_index_names) == sorted(expected_index_names), \
            f"Expected names {sorted(expected_index_names)}, got {sorted(actual_index_names)}"
        logger.info("Multiple index names verified successfully.")

    def test_5407(self):
        """Test case-sensitive regex pattern for listing indexes."""
        logger.info("Testing case-sensitive regex pattern for listing indexes...")
        indexes = self.vector_index.list("^TEST_VECTOR_INDEX?")
        assert any(idx.index_name == "TEST_VECTOR_INDEX2" for idx in indexes)
        logger.info("Case-sensitive pattern matched correctly.")

    def test_5408(self):
        """Test case-insensitive regex pattern for listing indexes."""
        logger.info("Testing case-insensitive regex pattern for listing indexes...")
        indexes = self.vector_index.list("^TEST")
        assert any(idx.index_name.upper() == "TEST_VECTOR_INDEX1" for idx in indexes)
        logger.info("Case-insensitive pattern matched correctly.")

    def test_5409(self):
        """Test complex regex pattern with OR operator."""
        logger.info("Testing complex regex pattern with OR operator...")
        indexes = self.vector_index.list("^(test_vector_index|test_vecidx)")
        names = [idx.index_name for idx in indexes]
        assert "TEST_VECTOR_INDEX1" in names
        assert "TEST_VECIDX1" in names
        assert "INVALID_VECIDX1" not in names
        logger.info("Complex regex OR pattern matched correctly.")

    # ----------------
    # Negative tests
    # ----------------
    def test_5410(self):
        """Test non-matching regex pattern returns nothing."""
        logger.info("Testing non-matching regex pattern...")
        indexes = self.vector_index.list(index_name_pattern="^xyz")
        assert len(list(indexes)) == 0
        logger.info("Non-matching pattern returned no results as expected.")

    def test_5411(self):
        """Test invalid regex pattern expecting ORA-12726 error."""
        logger.info("Testing invalid regex pattern expecting ORA-12726 error...")
        with pytest.raises(oracledb.DatabaseError) as cm:
            list(self.vector_index.list("[unclosed"))
        assert "ORA-12726" in str(cm.value)
        logger.info("Invalid regex correctly raised ORA-12726 error.")

    def test_5412(self):
        """Test invalid type pattern (numeric instead of string)."""
        logger.info("Testing invalid type pattern (numeric instead of string)...")
        indexes = list(self.vector_index.list(123))
        assert len(indexes) == 0
        logger.info("Invalid type pattern handled correctly with empty result.")

    # ----------------
    # Stress / Edge cases
    # ----------------
    def test_5413(self):
        """Test None as pattern input."""
        logger.info("Testing None as pattern input...")
        indexes = self.vector_index.list(None)
        assert len(list(indexes)) != len(self.indexes)
        logger.info("None pattern handled correctly.")

    def test_5414(self):
        """Test empty string as pattern input."""
        logger.info("Testing empty string as pattern input...")
        indexes = self.vector_index.list("")
        assert len(list(indexes)) != len(self.indexes)
        logger.info("Empty string pattern handled correctly.")

    def test_5415(self):
        """Test whitespace-only pattern."""
        logger.info("Testing whitespace-only pattern...")
        indexes = self.vector_index.list(" ")
        assert len(list(indexes)) == 0
        logger.info("Whitespace pattern correctly returned no matches.")

    def test_5416(self):
        """Test numeric string pattern yields no matches."""
        logger.info("Testing numeric pattern that should yield no matches...")
        indexes = list(self.vector_index.list("test123"))
        assert len(indexes) == 0
        logger.info("Numeric pattern correctly returned no matches.")

    def test_5417(self):
        """Test pattern with special characters '$'."""
        logger.info("Testing pattern with special characters '$'...")
        indexes = self.vector_index.list("test_vector_index1$")
        assert len(list(indexes)) == 1
        logger.info("Special character pattern matched correctly.")

    def test_5418(self):
        """Test extremely long regex pattern expecting ORA-12733 error."""
        logger.info("Testing extremely long regex pattern expecting ORA-12733 error...")
        pattern = "^" + "a" * 1000 + "$"
        with pytest.raises(oracledb.DatabaseError) as cm:
            list(self.vector_index.list(pattern))
        assert "ORA-12733" in str(cm.value)
        logger.info("Long regex correctly raised ORA-12733 error.")

    def test_5419(self):
        """Test case-insensitive match for prefix."""
        logger.info("Testing case-insensitive match for prefix '^TEST'...")
        indexes = self.vector_index.list("^TEST")
        assert len(list(indexes)) == 7
        logger.info("Case-insensitive match returned expected count.")

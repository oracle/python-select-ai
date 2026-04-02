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
import time
from select_ai import OracleVectorIndexAttributes

# Set up global logger (one per module)
logger = logging.getLogger("TestDeleteVectorIndex")

@pytest.fixture(scope="class", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO
    )

@pytest.fixture(scope="class")
def delete_vec_params(request):
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
    request.cls.delete_vec_params = params

@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown(request, delete_vec_params):
    logger.info("=== Setting up TestDeleteVectorIndex class ===")
    test_env.create_connection(use_wallet=request.cls.delete_vec_params["use_wallet"])
    assert select_ai.is_connected(), "Connection to DB failed"
    logger.info("Fetching credential secrets and OCI configuration...")
    request.cls.create_credential()
    request.cls.profile = request.cls.create_profile()
    logger.info("Setup complete.")
    yield
    logger.info("=== Tearing down TestDeleteVectorIndex class ===")
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

@pytest.mark.usefixtures("delete_vec_params", "setup_and_teardown")
class TestDeleteVectorIndex:
    @classmethod
    def get_native_cred_param(cls, cred_name=None) -> dict:
        logger.info(f"Preparing native credential params for: {cred_name}")
        params = cls.delete_vec_params
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
        params = cls.delete_vec_params
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
            logger.error(f"create_credential() raised {e} unexpectedly.")
            raise AssertionError(f"create_credential() raised {e} unexpectedly.")
        try:
            logger.info(f"Creating ObjectStore credential: {objstore_cred}")
            select_ai.create_credential(credential=objstore_credential, replace=True)
            logger.info("ObjectStore credential created.")
        except Exception as e:
            logger.error(f"create_credential() raised {e} unexpectedly.")
            raise AssertionError(f"create_credential() raised {e} unexpectedly.")
    @classmethod
    def create_profile(cls, profile_name="vector_ai_profile"):
        logger.info(f"Creating Profile: {profile_name}")
        params = cls.delete_vec_params
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
            logger.error(f"profile.delete() raised {e} unexpectedly.")
            raise AssertionError(f"profile.delete() raised {e} unexpectedly.")
    @classmethod
    def delete_credential(cls):
        logger.info("Deleting credentials...")
        try:
            select_ai.delete_credential("GENAI_CRED", force=True)
            logger.info("Deleted credential 'GENAI_CRED'")
        except Exception as e:
            logger.error(f"delete_credential() raised {e} unexpectedly.")
            raise AssertionError(f"delete_credential() raised {e} unexpectedly.")
        try:
            select_ai.delete_credential("OBJSTORE_CRED", force=True)
            logger.info("Deleted credential 'OBJSTORE_CRED'")
        except Exception as e:
            logger.error(f"delete_credential() raised {e} unexpectedly.")
            raise AssertionError(f"delete_credential() raised {e} unexpectedly.")

    def delete_and_wait(self, force=True, pattern=".*", wait_seconds=1):
        logger.info("Deleting indexes matching pattern.")
        all_indexes = list(self.vecidx.list(index_name_pattern=pattern))
        if not all_indexes:
            logger.info("No indexes found to delete.")
            return
        for idx in all_indexes:
            try:
                idx.delete(force=force)
                logger.info(f"Deleted index: {idx.index_name}")
                time.sleep(wait_seconds)
            except Exception as e:
                logger.warning(f"Warning: failed to delete index {idx.index_name}: {e}")
        remaining = list(self.vecidx.list(index_name_pattern=pattern))
        logger.info(f"Remaining indexes after delete: {[i.index_name for i in remaining]}")

    def setup_method(self, method):
        logger.info(f"SetUp for {method.__name__}")
        self.objstore_cred = "OBJSTORE_CRED"
        self.vecidx = select_ai.VectorIndex()
        params = self.delete_vec_params
        self.vector_index_attributes = select_ai.OracleVectorIndexAttributes(
            location=params["embedding_location"],
            object_storage_credential_name=self.objstore_cred
        )
        self.delete_and_wait()
        self.index_name = "test_vector_index"
        self.vector_index = select_ai.VectorIndex(
            index_name=self.index_name,
            attributes=self.vector_index_attributes,
            description="Test vector index",
            profile=self.profile
        )
        self.vector_index.create(replace=True)
        logger.info(f"Vector index '{self.index_name}' created for test.")

    def teardown_method(self, method):
        logger.info(f"TearDown for {method.__name__}")
        try:
            self.vector_index.delete(force=True)
            logger.info(f"Vector index '{self.index_name}' deleted successfully.")
        except Exception as e:
            logger.warning(f"Warning: vector index cleanup failed: {e}")

    def assert_index_count(self, pattern, expected):
        actual = list(self.vecidx.list(index_name_pattern=pattern))
        logger.info(f"Indexes matching '{pattern}': {[i.index_name for i in actual]}")
        assert len(actual) == expected, f"Expected {expected} indexes, got {len(actual)}"

    def verify_and_cleanup_vectab(self, vector_index_name: str):
        table_name = f"{vector_index_name}$vectab".upper()
        logger.info(f"Verifying and cleaning up vector table: {table_name}")
        with select_ai.cursor() as cursor:
            cursor.execute("""
                SELECT column_name
                FROM user_tab_columns
                WHERE table_name = :table_name
                ORDER BY column_id
            """, {"table_name": table_name})
            cols = [c[0] for c in cursor.fetchall()]
            logger.info(f"Columns found in {table_name}: {cols}")
            expected_cols = ["CONTENT", "ATTRIBUTES", "EMBEDDING"]
            assert cols == expected_cols, f"Unexpected columns for {table_name}: {cols}"
            cursor.execute(f"DROP TABLE {table_name} PURGE")
            logger.info(f"Table {table_name} dropped successfully.")

    def test_5101(self):
        """Test single vector index deletion removes the index."""
        logger.info("Deleting vector index (single delete)")
        self.assert_index_count("^test_vector_index", 1)
        self.vector_index.delete(force=True)
        logger.info("Delete called on vector index.")
        time.sleep(1)
        self.assert_index_count("^test_vector_index", 0)
        logger.info("Single-delete verified: index removed")

    # def test_5102(self):
    #     """Test multiple creates then bulk delete."""
    #     logger.info("Creating multiple vector indexes")
    #     # Create multiple indexes
    #     for i in range(5):
    #         idx = select_ai.VectorIndex(
    #             index_name=f"TEST_VECTOR_INDEX_{i}",
    #             attributes=self.vector_index_attributes,
    #             profile=self.profile
    #         )
    #         idx.create(replace=True)
    #         logger.info(f"Created index TEST_VECTOR_INDEX_{i}")
    #     logger.info("Deleting all created indexes")
    #     # Delete all indexes one by one
    #     self.delete_and_wait(force=True, pattern=f"^TEST_VECTOR_INDEX_{i}$")
    #     # Ensure all are gone
    #     actual_indexes = list(self.vector_index.list(index_name_pattern="^TEST_VECTOR_INDEX_"))
    #     logger.info(f"Indexes found for bulk delete test: {actual_indexes}")
    #     assert len(actual_indexes) == 0
    #     logger.info("All TEST_VECTOR_INDEX_* deleted successfully.")

    def test_5103(self):
        """Test deleting the same vector index twice."""
        logger.info("Deleting vector index first time")
        self.vector_index.delete(force=True)
        logger.info("Deleting vector index second time (no-op expected)")
        time.sleep(1)
        self.vector_index.delete(force=True)  # no-op
        time.sleep(1)
        self.assert_index_count("^test_vector_index", 0)
        logger.info("Double-delete verified: index removed")

    def test_5104(self):
        """Test delete with include_data=True also removes table."""
        logger.info("Deleting index with include_data=True (metadata + table)")
        self.vector_index.delete(include_data=True, force=True)
        time.sleep(1)
        self.assert_index_count("^test_vector_index", 0)
        table_name = "TEST_VECTOR_INDEX$VECTAB"
        with select_ai.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*)
                FROM user_tables
                WHERE table_name = :table_name
            """, {"table_name": table_name})
            (count,) = cursor.fetchone()
        logger.info(f"Verified vector table '{table_name}' removed: {count==0}")
        assert count == 0

    def test_5105(self):
        """Test delete with include_data=False doesn't remove table."""
        logger.info("Deleting index with include_data=False (metadata only)")
        self.vector_index.delete(include_data=False, force=True)
        time.sleep(1)
        self.assert_index_count("^test_vector_index", 0)
        logger.info("Attempting to recreate index (should fail due to leftover table)")
        with pytest.raises(oracledb.DatabaseError) as cm:
            self.vector_index.create(replace=True)
        logger.info(f"Expected DatabaseError on recreate: {cm.value}")
        assert "ORA-00955" in str(cm.value)
        self.verify_and_cleanup_vectab("test_vector_index")
        logger.info("Vector table cleaned up after failed recreate")

    def test_5106(self):
        """Test delete twice with include_data=False then cleanup."""
        logger.info("Deleting index metadata only first time")
        self.vector_index.delete(include_data=False, force=True)
        time.sleep(1)
        self.assert_index_count("^test_vector_index", 0)
        logger.info("Attempting to recreate index (should fail)")
        with pytest.raises(oracledb.DatabaseError) as cm:
            self.vector_index.create(replace=True)
        assert "ORA-00955" in str(cm.value)
        self.verify_and_cleanup_vectab("test_vector_index")
        logger.info("Vector table cleaned up")
        logger.info("Deleting index metadata only second time (no-op)")
        self.vector_index.delete(include_data=False, force=True)
        self.assert_index_count("^test_vector_index", 0)

    def test_5107(self):
        """Test delete twice with include_data=False and cleanup after failed recreate."""
        logger.info("Deleting metadata only first time")
        self.vector_index.delete(include_data=False, force=True)
        time.sleep(1)
        self.assert_index_count("^test_vector_index", 0)
        logger.info("Attempting recreate (expected failure)")
        with pytest.raises(oracledb.DatabaseError) as cm:
            self.vector_index.create(replace=True)
        logger.info(f"Recreate failed (expected): {cm.value}")
        assert "ORA-00955" in str(cm.value)
        logger.info("Deleting metadata second time (no-op)")
        self.vector_index.delete(include_data=False, force=True)
        self.verify_and_cleanup_vectab("test_vector_index")
        self.assert_index_count("^test_vector_index", 0)
        logger.info("Cleanup complete")

    def test_5108(self):
        """Test delete and then recreate a vector index."""
        logger.info("Deleting index before recreation")
        self.vector_index.delete(force=True)
        time.sleep(1)
        logger.info("Recreating vector index")
        self.vector_index.create(replace=True)
        time.sleep(1)
        self.assert_index_count("^test_vector_index", 1)
        logger.info("Recreate verified: index exists")

    def test_5109(self):
        """Test delete of a nonexistent index (should not error)."""
        idx = select_ai.VectorIndex(
            index_name="nonexistent_index",
            attributes=self.vector_index_attributes,
            profile=self.profile
        )
        logger.info("Attempting to delete nonexistent index")
        idx.delete(force=True)
        time.sleep(1)
        self.assert_index_count("^nonexistent_index", 0)
        logger.info("Nonexistent delete verified (no error)")

    def test_5110(self):
        """Test delete after set_attributes was called."""
        logger.info("Setting temporary attributes before delete")
        self.vector_index.create(replace=True)
        try:
            self.vector_index.set_attributes(
                attribute_name="match_limit",
                attribute_value=10
            )
        except Exception as e:
            logger.error(f"set_attributes() raised {e} unexpectedly.")
            pytest.fail(f"set_attributes() raised {e} unexpectedly.")
        logger.info("Deleting index after setting attributes")
        self.vector_index.delete(force=True)
        time.sleep(1)
        actual_indexes = list(self.vector_index.list(index_name_pattern="^test_vector_index$"))
        logger.info(f"Indexes remaining after delete: {actual_indexes}")
        assert len(actual_indexes) == 0
        logger.info("Delete after attributes verified")

    def test_5111(self):
        """Test case-sensitive name for create and delete."""
        idx = select_ai.VectorIndex(
            index_name="CaseSensitiveIndex",
            attributes=self.vector_index_attributes,
            profile=self.profile
        )
        logger.info("Creating case-sensitive index")
        idx.create(replace=True)
        logger.info("Deleting case-sensitive index")
        idx.delete(force=True)
        time.sleep(1)
        self.assert_index_count("^CaseSensitiveIndex", 0)
        logger.info("Case-sensitive index delete verified")

    def test_5112(self):
        """Test creation and deletion with long index name."""
        long_name = "index_" + "x" * 40
        idx = select_ai.VectorIndex(
            index_name=long_name,
            attributes=self.vector_index_attributes,
            profile=self.profile
        )
        logger.info(f"Creating long-name index: {long_name}")
        idx.create(replace=True)
        logger.info(f"Deleting long-name index: {long_name}")
        idx.delete(force=True)
        time.sleep(1)
        self.assert_index_count(f"^{long_name}$", 0)
        logger.info("Long-name index delete verified")

    def test_5113(self):
        """Test creation and bulk deletion of indexes."""
        names = [f"bulk_idx_{i}" for i in range(3)]
        logger.info("Creating bulk indexes")
        for n in names:
            select_ai.VectorIndex(
                index_name=n,
                attributes=self.vector_index_attributes,
                profile=self.profile
            ).create(replace=True)
            logger.info(f"Created {n}")
        logger.info("Deleting bulk indexes")
        for n in names:
            select_ai.VectorIndex(
                index_name=n,
                attributes=self.vector_index_attributes,
                profile=self.profile
            ).delete(force=True)
            time.sleep(1)
            logger.info(f"Deleted {n}")
        self.assert_index_count("^bulk_idx_", 0)
        logger.info("Bulk delete verified")

    def test_5114(self):
        """Test that list returns empty after index is deleted."""
        logger.info("Deleting index and verifying list is empty")
        self.vector_index.delete(force=True)
        time.sleep(1)
        actual_indexes = list(self.vector_index.list(index_name_pattern=".*"))
        index_names = [idx.index_name for idx in actual_indexes]
        logger.info(f"Actual indexes after delete: {index_names}")
        actual = list(self.vector_index.list(index_name_pattern="^test_vector_index"))
        assert actual == []
        logger.info("List verification successful: no remaining indexes")

    def test_5115(self):
        """Test delete then recreate index with same name."""
        logger.info("Deleting index before recreate with same name")
        self.vector_index.delete(force=True)
        time.sleep(1)
        logger.info("Recreating index with same name")
        self.vector_index.create(replace=False)
        time.sleep(1)
        self.assert_index_count("^test_vector_index", 1)
        logger.info("Recreate same-name index verified")

    def test_5116(self):
        """Test delete of one out of multiple indexes."""
        idx1 = select_ai.VectorIndex(index_name="IDX_1", attributes=self.vector_index_attributes, profile=self.profile)
        idx2 = select_ai.VectorIndex(index_name="IDX_2", attributes=self.vector_index_attributes, profile=self.profile)
        logger.info("Creating two indexes IDX_1 and IDX_2")
        idx1.create(replace=True)
        idx2.create(replace=True)
        logger.info("Deleting IDX_1 only")
        self.delete_and_wait(force=True, pattern="^IDX_1$")
        remaining_idx2 = list(self.vector_index.list(index_name_pattern="^IDX_2$"))
        logger.info(f"IDX_2 entries after IDX_1 delete: {remaining_idx2}")
        assert len(remaining_idx2) == 1
        logger.info("IDX_2 remains after IDX_1 delete")

    def test_5117(self):
        """Test deletion by pattern."""
        logger.info("Deleting index with pattern '^test_vector_index$'")
        self.vector_index.create(replace=True)
        self.vector_index.delete(force=True)
        time.sleep(1)
        actual = list(self.vector_index.list(index_name_pattern="^test_vector_index$"))
        logger.info(f"List entries after pattern delete: {actual}")
        assert len(actual) == 0
        logger.info("Pattern delete verified")

    def test_5118(self):
        """Test delete with force=True option."""
        logger.info("Deleting index with force=True")
        self.vector_index.create(replace=True)
        self.vector_index.delete(force=True)
        time.sleep(1)
        self.assert_index_count("^test_vector_index$", 0)
        logger.info("Force delete verified")

    def test_5119(self):
        """Test delete with force=False option."""
        logger.info("Creating index before delete (force=False)")
        self.vector_index.create(replace=True)
        logger.info("Deleting index with force=False")
        self.vector_index.delete(force=False)
        time.sleep(1)
        self.assert_index_count("^test_vector_index$", 0)
        logger.info("Delete verified successfully with force=False")

    def test_5120(self):
        """Test delete with force=False called twice in a row."""
        logger.info("Deleting index first time (force=False)")
        self.vector_index.delete(force=False)
        time.sleep(1)
        self.assert_index_count("^test_vector_index$", 0)
        logger.info("First delete succeeded")
        logger.info("Attempting second delete (expected to fail)")
        with pytest.raises(Exception) as cm:
            self.vector_index.delete(force=False)
        assert "does not exist" in str(cm.value)
        logger.info(f"Expected failure confirmed: {cm.value}")
        self.assert_index_count("^test_vector_index$", 0)
        logger.info("Index still absent after failed second delete")

    def test_5121(self):
        """Test delete include_data=False and force=False (leftover vectab)"""
        logger.info("Deleting index with include_data=False and force=False")
        self.vector_index.delete(include_data=False, force=False)
        time.sleep(1)
        self.assert_index_count("^test_vector_index", 0)
        logger.info("Attempting to recreate index (expected to fail - leftover data)")
        with pytest.raises(oracledb.DatabaseError) as cm:
            self.vector_index.create(replace=False)
        assert "ORA-00955" in str(cm.value)
        logger.info(f"Expected recreate failure confirmed: {cm.value}")
        logger.info("Cleaning up leftover vector table")
        self.verify_and_cleanup_vectab("test_vector_index")
        logger.info("Cleanup complete after include_data=False, force=False delete")

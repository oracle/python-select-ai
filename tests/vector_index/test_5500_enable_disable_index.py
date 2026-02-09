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
from select_ai import VectorIndex

# Set up global logger (one per module)
logger = logging.getLogger("TestEnableDisableVectorIndex")

@pytest.fixture(scope="class", autouse=True)
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO
    )

@pytest.fixture(scope="class")
def enabledisable_params(request):
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
    request.cls.enabledisable_params = params

@pytest.fixture(scope="class", autouse=True)
def setup_and_teardown(request, enabledisable_params):
    logger.info("=== Setting up TestEnableDisableVectorIndex class ===")
    p = request.cls.enabledisable_params
    test_env.create_connection(use_wallet=p["use_wallet"])
    assert select_ai.is_connected(), "Connection to DB failed"
    logger.info("Fetching credential secrets and OCI configuration...")

    # table setup
    with select_ai.cursor() as cursor:
        cursor.execute("begin execute immediate 'drop table test_items purge'; exception when others then null; end;")
        cursor.execute("create table test_items (id number primary key, name varchar2(50))")
        cursor.execute("insert into test_items values (1, 'Alpha')")
        cursor.execute("insert into test_items values (2, 'Beta')")
        cursor.execute("commit")

    # test resources
    request.cls.create_credential()
    request.cls.profile = request.cls.create_profile()
    logger.info("Setup complete.")

    # Start with clean vector index
    vi_attrs = select_ai.OracleVectorIndexAttributes(
        location=p["embedding_location"],
        object_storage_credential_name="OBJSTORE_CRED"
    )
    request.cls.vector_index_attributes = vi_attrs
    request.cls.index_name = "test_vector_index"
    vector_index = select_ai.VectorIndex(
        index_name=request.cls.index_name,
        attributes=vi_attrs,
        description="Test vector index",
        profile=request.cls.profile
    )
    vector_index.create(replace=True)
    created_indexes = [idx.index_name for idx in VectorIndex.list()]
    assert request.cls.index_name.upper() in created_indexes, f"VectorIndex {request.cls.index_name} was not created"

    yield

    logger.info("=== Tearing down TestEnableDisableVectorIndex class ===")
    try:
        vector_index = VectorIndex(index_name=request.cls.index_name)
        vector_index.delete(force=True)
    except Exception as e:
        logger.info(f"Warning: drop vector index failed: {e}")
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

@pytest.mark.usefixtures("enabledisable_params", "setup_and_teardown")
class TestEnableDisableVectorIndex:
    @classmethod
    def get_native_cred_param(cls, cred_name=None) -> dict:
        logger.info(f"Preparing native credential params for: {cred_name}")
        p = cls.enabledisable_params
        return dict(
            credential_name = cred_name,
            user_ocid       = p["user_ocid"],
            tenancy_ocid    = p["tenancy_ocid"],
            private_key     = p["private_key"],
            fingerprint     = p["fingerprint"]
        )
    @classmethod
    def get_cred_param(cls, cred_name=None) -> dict:
        logger.info(f"Preparing basic credential params for: {cred_name}")
        p = cls.enabledisable_params
        return dict(
            credential_name = cred_name,
            username        = p["cred_username"],
            password        = p["cred_password"]
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
        p = cls.enabledisable_params
        provider = select_ai.OCIGenAIProvider(
            oci_compartment_id=p["oci_compartment_id"],
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
    def setup_method(self, method):
        logger.info(f"SetUp for {method.__name__}")
        self.objstore_cred = "OBJSTORE_CRED"
        self.vecidx = select_ai.VectorIndex()
        self.vector_index = list(self.vecidx.list(index_name_pattern=".*"))[0]
        logger.info(self.vector_index.index_name)
        try:
            self.vector_index.enable()
            time.sleep(1)
        except oracledb.DatabaseError as e:
            if "ORA-20000" not in str(e):
                raise
    def teardown_method(self, method):
        logger.info(f"TearDown for {method.__name__}")

    def wait_for_status_table(self, cursor, status_table, retries=5, delay=2):
        for _ in range(retries):
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {status_table}")
                return cursor.fetchone()
            except oracledb.DatabaseError as e:
                if "ORA-00942" in str(e):
                    time.sleep(delay)
                    continue
                raise
        return None

    def wait_for_pipeline_entry(self, cursor, pipeline_name, retries=5, delay=2):
        for _ in range(retries):
            cursor.execute(
                "SELECT status_table FROM user_cloud_pipelines WHERE pipeline_name = :1",
                [pipeline_name]
            )
            row = cursor.fetchone()
            if row and row[0]:
                return row[0]
            time.sleep(delay)
        return None

    def test_5501(self):
        """Disabling and enabling the vector index."""
        logger.info(f"Disabling vector index: {self.index_name}")
        self.vector_index.disable()
        logger.info(f"Enabling vector index: {self.index_name}")
        self.vector_index.enable()
        logger.info(f"Vector index enabled successfully")

    def test_5502(self):
        """Disable same vector index twice (should be harmless)."""
        logger.info(f"First disable of vector index: {self.index_name}")
        self.vector_index.disable()
        logger.info(f"Attempting second disable of vector index: {self.index_name}")
        self.vector_index.disable()

    def test_5503(self):
        """Enable same vector index twice (should be harmless)."""
        logger.info(f"Enabling vector index: {self.index_name}")
        self.vector_index.enable()
        self.vector_index.enable()

    def test_5504(self):
        """Ensure queries work after enabling the vector index."""
        logger.info("Querying test_items table after enabling vector index")
        with select_ai.cursor() as cursor:
            cursor.execute("select count(*) from test_items")
            row_count, = cursor.fetchone()
            logger.info(f"Number of rows in test_items: {row_count}")
        df = self.profile.run_sql(prompt="How many rows in test_items")
        logger.info(f"run_sql returned: {df}")
        assert len(df) > 0, "run_sql should return rows when index is enabled"

    def test_5505(self):
        """Ensure queries fail after disabling the vector index."""
        logger.info(f"Disabling vector index: {self.index_name} to test query blocking")
        self.vector_index.disable()
        logger.info(f"Running query should raise DatabaseError")
        with pytest.raises(oracledb.DatabaseError) as cm:
            self.profile.run_sql(prompt="Show all rows from test_items")
        logger.info(f"Expected database error confirmed: {cm.value}")

    def test_5506(self):
        """Disabling a nonexistent index raises error."""
        logger.info("Disabling nonexistent index to test error handling")
        invalid_index = VectorIndex(index_name="does_not_exist")
        with pytest.raises(oracledb.DatabaseError) as cm:
            invalid_index.disable()
        logger.info(f"Expected database error confirmed: {cm.value}")

    def test_5507(self):
        """Enabling a nonexistent index raises error."""
        logger.info("Enabling nonexistent index to test error handling")
        invalid_index = VectorIndex(index_name="does_not_exist")
        with pytest.raises(oracledb.DatabaseError) as cm:
            invalid_index.enable()
        logger.info(f"Expected database error confirmed: {cm.value}")

    def test_5508(self):
        """Disabling after delete raises error; vector index recreated."""
        logger.info(f"Deleting vector index: {self.index_name}")
        self.vector_index.delete(force=True)
        logger.info(f"Attempting to disable deleted index")
        with pytest.raises(oracledb.DatabaseError):
            self.vector_index.disable()
        logger.info(f"Recreating vector index for subsequent tests")
        vector_index = select_ai.VectorIndex(
            index_name=self.index_name,
            attributes=self.vector_index_attributes,
            description="Test vector index",
            profile=self.profile
        )
        vector_index.create(replace=True)
        logger.info(f"Vector index recreated successfully")

    def test_5509(self):
        """Pipeline inactive after disabling the vector index."""
        logger.info(f"Disabling vector index: {self.index_name} to check pipeline inactivity")
        self.vector_index.disable()
        pipeline_name = f"{self.index_name.upper()}$VECPIPELINE"
        with select_ai.cursor() as cursor:
            cursor.execute(
                "SELECT status_table FROM user_cloud_pipelines WHERE pipeline_name = :1",
                [pipeline_name]
            )
            row = cursor.fetchone()
            if row is None:
                logger.info(f"Pipeline is inactive (no entry in user_cloud_pipelines)")
                assert True
                return
            status_table = row[0]
            logger.info(f"Status table found: {status_table}, querying should fail")
            with pytest.raises(oracledb.DatabaseError):
                cursor.execute(f"SELECT * FROM {status_table} FETCH FIRST 1 ROWS ONLY")

    def test_5510(self):
        """Pipeline active after enabling the vector index."""
        pipeline_name = f"{self.index_name.upper()}$VECPIPELINE"
        logger.info(f"Checking pipeline activity after enabling vector index")
        with select_ai.cursor() as cursor:
            cursor.execute(
                "SELECT status_table FROM user_cloud_pipelines WHERE pipeline_name = :pipeline_name",
                {"pipeline_name": pipeline_name}
            )
            (status_table,) = cursor.fetchone()
            logger.info(f"Status table found: {status_table}")
            assert status_table is not None, f"No pipeline entry found for {pipeline_name}"
            count_row = self.wait_for_status_table(cursor, status_table)
        assert count_row is not None, f"No result returned from status_table {status_table}"
        assert count_row[0] >= 0, "Pipeline table should be accessible when enabled"
        logger.info(f"Pipeline is active and accessible")

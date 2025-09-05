import unittest
import select_ai
import test_env
import oracledb
import os
import time


class TestCreateVectorIndex(unittest.TestCase):
    @classmethod
    def get_native_cred_param(cls, cred_name=None) -> dict:
        return dict(
            credential_name = cred_name,
            user_ocid       = cls.user_ocid,
            tenancy_ocid    = cls.tenancy_ocid,
            private_key     = cls.private_key,
            fingerprint     = cls.fingerprint
        )
    
    
    @classmethod
    def get_cred_param(cls, cred_name=None) -> dict:
        return dict(
            credential_name = cred_name,
            username        = cls.cred_username,
            password        = cls.cred_password
        )
    
    
    @classmethod
    def create_credential(cls, genai_cred="GENAI_CRED", objstore_cred="OBJSTORE_CRED"):
        # Get credential secret
        genai_credential = cls.get_native_cred_param(genai_cred)
        objstore_credential = cls.get_cred_param(objstore_cred)

        # Create GenAI Credential
        try:
            select_ai.create_credential(credential=genai_credential, replace=True)
        except Exception as e:
            raise AssertionError(f"create_credential() raised {e} unexpectedly.")
        
        # Create ObjStore Credential
        try:
            select_ai.create_credential(credential=objstore_credential, replace=True)
        except Exception as e:
            raise AssertionError(f"create_credential() raised {e} unexpectedly.")
    

    @classmethod
    def create_profile(cls, profile_name="vector_ai_profile"):
        provider = select_ai.OCIGenAIProvider(
            oci_compartment_id=cls.oci_compartment_id,
            oci_apiformat="GENERIC"
        )
        profile_attributes = select_ai.ProfileAttributes(
            credential_name="GENAI_CRED",
            provider=provider
        )
        cls.profile = select_ai.Profile(
            profile_name=profile_name,
            attributes=profile_attributes,
            description="OCI GENAI Profile",
            replace=True
        )


    @classmethod
    def delete_profile(cls):
        try:
            cls.profile.delete()
        except Exception as e:
            raise AssertionError(f"profile.delete() raised {e} unexpectedly.")


    @classmethod
    def delete_credential(cls):
        try:
            select_ai.delete_credential("GENAI_CRED", force=True)
        except Exception as e:
            self.fail(f"delete_credential() raised {e} unexpectedly.")

        try:
            select_ai.delete_credential("OBJSTORE_CRED", force=True)
        except Exception as e:
            self.fail(f"delete_credential() raised {e} unexpectedly.")


    @classmethod
    def setUpClass(cls):
        """
        Create Credential, Profile once before all tests.
        """
        # Assign password from test_env
        cls.user = test_env.get_test_user()
        cls.password = test_env.get_test_password()
        cls.dsn = test_env.get_localhost_connect_string()

        # Create connection
        # test_env.create_connection()
        test_env.create_connection(
            dsn=cls.dsn, use_wallet=False
        )
        assert select_ai.is_connected(), "Connection to DB failed"

        # Get Native cred secrets
        cls.user_ocid = test_env.get_user_ocid()
        cls.tenancy_ocid = test_env.get_tenancy_ocid()
        cls.private_key = test_env.get_private_key()
        cls.fingerprint = test_env.get_fingerprint()

        # Get basic cred secrets
        cls.cred_username = test_env.get_cred_username()
        cls.cred_password = test_env.get_cred_password()

        # Get OCI Provider
        cls.oci_compartment_id = test_env.get_compartment_id()
        cls.embedding_location = test_env.get_embedding_location()

        # Create Credential
        cls.create_credential()
        # Create Profile
        cls.create_profile()

    
    @classmethod
    def tearDownClass(cls):
        # Delete Profile
        cls.delete_profile()

        # Delete Credential
        cls.delete_credential()

        # Disconnect from DB
        try:
            select_ai.disconnect()
        except Exception as e:
            print(f"Warning: disconnect failed ({e})")


    def setUp(self):
        self.embedding_location = self.__class__.embedding_location
        self.profile = self.__class__.profile
        self.dsn = self.__class__.dsn
        self.objstore_cred = "OBJSTORE_CRED"

        # Specify objects to create an embedding for.
        # The objects reside in ObjectStore and the vector database is Oracle
        self.vector_index_attributes = select_ai.OracleVectorIndexAttributes(
            location=self.embedding_location,
            object_storage_credential_name=self.objstore_cred
        )

        # Create vector index object
        self.vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            description="Test vector index",
            profile=self.profile
        )
    

    def tearDown(self):
        # Delete Vector Index
        vector_index = select_ai.VectorIndex(index_name="test_vector_index")
        vector_index.delete(force=True)
    

    def test_create_vector_index_success(self):
        try:
            self.vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")

        # Verify list
        vector_index = select_ai.VectorIndex()
        indexes = [i.index_name for i in vector_index.list()]
        self.assertIn("TEST_VECTOR_INDEX", indexes)
    
    
    def test_create_vector_index_success_replace_false(self):
        try:
            self.vector_index.create(replace=False)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")

        # Verify list
        vector_index = select_ai.VectorIndex()
        indexes = [i.index_name for i in vector_index.list()]
        self.assertIn("TEST_VECTOR_INDEX", indexes)


    def test_create_vector_index_empty_description(self):
        # Create vector index object
        vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            description="",
            profile=self.profile
        )
        try:
            vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")
      
        # Verify list
        vector_index = select_ai.VectorIndex()
        indexes = [i.index_name for i in vector_index.list()]
        self.assertIn("TEST_VECTOR_INDEX", indexes)
    

    def test_create_vector_index_replace_true(self):
        # First creation
        try:
            self.vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")

        # Second creation
        try:
            self.vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")

    
    def test_create_vector_index_replace_false(self):
        # First creation should succeed
        try:
            self.vector_index.create(replace=False)
        except Exception as e:
            self.fail(f"Create vector index failed unexpectedly with exception: {e}")

        # Second creation should raise ORA-20048
        with self.assertRaises(oracledb.DatabaseError) as cm:
            self.vector_index.create(replace=False)

        # Verify the error code/message
        self.assertIn("ORA-20048", str(cm.exception))
        self.assertIn("already exists", str(cm.exception))
    

    def test_create_vector_index_minimal_attributes(self):
        # Create vector index object
        vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            profile=self.profile
        )

        try:
            vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")

    
    def test_create_vector_index_recreate_after_delete(self):
        try:
            self.vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")
      
        # Delete Vector Index
        vector_index = select_ai.VectorIndex(index_name="test_vector_index")
        vector_index.delete(force=True)

        try:
            self.vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")


    # Negative Case
    def test_create_vector_index_invalid_credential(self):
        vector_index_attributes = select_ai.OracleVectorIndexAttributes(
            location=self.embedding_location,
            object_storage_credential_name="invalidObjStore_cred"
        )

        # Create vector index object
        vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.profile
        )

        with self.assertRaises(oracledb.DatabaseError):
            vector_index.create(replace=True)

    def test_create_vector_index_invalid_location(self):
        vector_index_attributes = select_ai.OracleVectorIndexAttributes(
            location="invalid_location",
            object_storage_credential_name=self.objstore_cred
        )

        # Create vector index object
        vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.profile
        )

        with self.assertRaises(oracledb.DatabaseError):
            vector_index.create(replace=True)
  
    
    def test_create_vector_index_missing_attributes(self):
        with self.assertRaises(AttributeError):
            select_ai.VectorIndex(
                  index_name="test_vector_index",
                  attributes=None,
                  profile=self.profile
            ).create()
    
    
    def test_create_vector_index_invalid_attributes_type(self):
        with self.assertRaises(TypeError):
            select_ai.VectorIndex(
                index_name="test_vector_index",
                attributes="invalid_attributes",  # invalid type
                profile=self.profile
            ).create()

    
    def test_create_vector_index_invalid_name_type(self):
        with self.assertRaises(oracledb.DatabaseError) as cm:
            select_ai.VectorIndex(
                index_name=12345,  # invalid type (int instead of str)
                attributes=self.vector_index_attributes,
                profile=self.profile
            ).create()

        # Verify error
        self.assertIn("ORA-20048", str(cm.exception))
        self.assertIn("Invalid vector index name", str(cm.exception))
    

    def test_create_vector_index_empty_name(self):
        with self.assertRaises(oracledb.DatabaseError) as cm:
            select_ai.VectorIndex(
                index_name="",
                attributes=self.vector_index_attributes,
                profile=self.profile
            ).create()

        # Verify the error code/message
        self.assertIn("ORA-20048", str(cm.exception))
        self.assertIn("Missing vector index name", str(cm.exception))
    

    def test_create_vector_index_invalid_profile(self):
        # Create vector index object
        vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            description="Test vector index",
            profile="invalid_profile"
        )
        with self.assertRaises(ValueError):
            vector_index.create()

    
    def test_create_vector_index_none_attributes(self):
        vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=None,
            description="Test vector index",
            profile="invalid_profile"
        )
        with self.assertRaises(TypeError):
            vector_index.create()


    # Boundary Cases
    def test_create_vector_index_long_name(self):
        long_name = "X" * 150  # > Oracle identifier length
        vector_index = select_ai.VectorIndex(
            index_name=long_name,
            attributes=self.vector_index_attributes,
            profile=self.profile
        )
        with self.assertRaises(oracledb.DatabaseError):
            vector_index.create()
    
    
    def test_create_vector_index_long_description(self):
        long_desc = "D" * 5000  # deliberately too long

        # Create vector index object
        vector_index = select_ai.VectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            description=long_desc,
            profile=self.profile
        )

        # Expect DatabaseError due to description length
        with self.assertRaises(oracledb.DatabaseError) as cm:
            vector_index.create(replace=True)

        # Verify Oracle error details
        self.assertIn("ORA-20045", str(cm.exception))
        self.assertIn("description is too long", str(cm.exception))

    
    def test_create_vector_index_multiple_recreates(self):
        for _ in range(10):
            self.vector_index.create(replace=True)



if __name__ == "__main__":
    test_env.run_test_cases()
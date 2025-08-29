import unittest
import select_ai
import test_env
import oracledb
import os
import asyncio


class TestAsyncCreateVectorIndex(unittest.IsolatedAsyncioTestCase):
    def get_native_cred_param(self, cred_name=None) -> dict:
        return dict(
            credential_name = cred_name,
            user_ocid       = self.__class__.user_ocid,
            tenancy_ocid    = self.__class__.tenancy_ocid,
            private_key     = self.__class__.private_key,
            fingerprint     = self.__class__.fingerprint
        )
    

    def get_cred_param(self, cred_name=None) -> dict:
        return dict(
            credential_name = cred_name,
            username        = self.__class__.cred_username,
            password        = self.__class__.cred_password
        )
    

    async def create_async_credential(self, genai_cred="GENAI_CRED", objstore_cred="OBJSTORE_CRED"):
        # Get credential secret
        genai_credential = self.get_native_cred_param(genai_cred)
        objstore_credential = self.get_cred_param(objstore_cred)

        # Create GenAI Credential
        try:
            await select_ai.async_create_credential(credential=genai_credential, replace=True)
        except Exception as e:
            raise AssertionError(f"create_credential() raised {e} unexpectedly.")
        
        # Create ObjStore Credential
        try:
            await select_ai.async_create_credential(credential=objstore_credential, replace=True)
        except Exception as e:
            raise AssertionError(f"create_credential() raised {e} unexpectedly.")
    

    async def create_async_profile(self, profile_name="vector_ai_profile"):
        provider = select_ai.OCIGenAIProvider(
            oci_compartment_id=self.__class__.oci_compartment_id,
            oci_apiformat="GENERIC"
        )
        profile_attributes = select_ai.ProfileAttributes(
            credential_name="GENAI_CRED",
            provider=provider
        )
        self.async_profile = await select_ai.AsyncProfile(
            profile_name=profile_name,
            attributes=profile_attributes,
            description="OCI GENAI Profile",
            replace=True
        )


    async def delete_async_profile(self):
        try:
            await self.async_profile.delete()
        except Exception as e:
            raise AssertionError(f"profile.delete() raised {e} unexpectedly.")
    
    
    async def delete_async_credential(self, genai_cred="GENAI_CRED", objstore_cred="OBJSTORE_CRED"):
        # Create GenAI Credential
        try:
            await select_ai.async_delete_credential(genai_cred, force=True)
        except Exception as e:
            raise AssertionError(f"delete_credential() raised {e} unexpectedly.")
        
        # Create ObjStore Credential
        try:
            await select_ai.async_delete_credential(objstore_cred, force=True)
        except Exception as e:
            raise AssertionError(f"delete_credential() raised {e} unexpectedly.")


    @classmethod
    def setUpClass(cls):
        """
        Get Env Variabels
        """
        # Assign password from test_env
        cls.user = test_env.get_test_user()
        cls.password = test_env.get_test_password()
        cls.dsn = test_env.get_localhost_connect_string()
      
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


    async def asyncSetUp(self):
        self.embedding_location = self.__class__.embedding_location
        self.dsn = self.__class__.dsn
        self.objstore_cred = "OBJSTORE_CRED"

        """
        Create Credential, Profile for all tests.
        """
        # Create async connection
        await test_env.create_async_connection(
            dsn=self.dsn, use_wallet=False
        )
        is_connected = await select_ai.async_is_connected()
        assert is_connected, "Connection to DB failed"

        # Create Credential
        await self.create_async_credential()
        # Create Profile
        await self.create_async_profile()

        # Specify objects to create an embedding for.
        # The objects reside in ObjectStore and the vector database is Oracle
        self.vector_index_attributes = select_ai.OracleVectorIndexAttributes(
            location=self.embedding_location,
            object_storage_credential_name=self.objstore_cred
        )

        # Create vector index object
        self.async_vector_index = select_ai.AsyncVectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            description="Test vector index",
            profile=self.async_profile
        )
    

    async def asyncTearDown(self):
        # Delete Vector Index
        async_vector_index = select_ai.AsyncVectorIndex(index_name="test_vector_index")
        await async_vector_index.delete(force=True)

        # Delete Profile
        await self.delete_async_profile()

        # Delete Credentials
        await self.delete_async_credential()

        # Disconnect from DB
        try:
            await select_ai.async_disconnect()
        except Exception as e:
            print(f"Warning: disconnect failed ({e})")
    

    async def test_async_create_vector_index_success(self):
        try:
            await self.async_vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")

        # Verify list
        async_vector_index = select_ai.AsyncVectorIndex()
        indexes = [i.index_name async for i in async_vector_index.list()]
        self.assertIn("TEST_VECTOR_INDEX", indexes)
    
    
    async def test_async_create_vector_index_success_replace_false(self):
        try:
            await self.async_vector_index.create(replace=False)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")

        # Verify list
        async_vector_index = select_ai.AsyncVectorIndex()
        indexes = [i.index_name async for i in async_vector_index.list()]
        self.assertIn("TEST_VECTOR_INDEX", indexes)


    async def test_async_create_vector_index_empty_description(self):
        # Create vector index object
        async_vector_index = select_ai.AsyncVectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            description="",
            profile=self.async_profile
        )
        try:
            await async_vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")
      
        # Verify list
        async_vector_index = select_ai.AsyncVectorIndex()
        indexes = [i.index_name async for i in async_vector_index.list()]
        self.assertIn("TEST_VECTOR_INDEX", indexes)
    

    async def test_async_create_vector_index_replace_true(self):
        # First creation
        try:
            await self.async_vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")

        # Second creation
        try:
            await self.async_vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")

    
    async def test_async_create_vector_index_replace_false(self):
        # First creation should succeed
        try:
            await self.async_vector_index.create(replace=False)
        except Exception as e:
            self.fail(f"Create vector index failed unexpectedly with exception: {e}")

        # Second creation should raise ORA-20048
        with self.assertRaises(oracledb.DatabaseError) as cm:
            await self.async_vector_index.create(replace=False)

        # Verify the error code/message
        self.assertIn("ORA-20048", str(cm.exception))
        self.assertIn("already exists", str(cm.exception))
    

    async def test_async_create_vector_index_minimal_attributes(self):
        # Create vector index object
        async_vector_index = select_ai.AsyncVectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            profile=self.async_profile
        )

        try:
            await async_vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")

    
    async def test_async_create_vector_index_recreate_after_delete(self):
        try:
            await self.async_vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")
      
        # Delete Vector Index
        async_vector_index = select_ai.AsyncVectorIndex(index_name="test_vector_index")
        await async_vector_index.delete(force=True)

        try:
            self.async_vector_index.create(replace=True)
        except Exception as e:
            self.fail(f"VectorIndex.create raised an unexpected exception: {e}")


    # Negative Case
    async def test_async_create_vector_index_invalid_credential(self):
        vector_index_attributes = select_ai.OracleVectorIndexAttributes(
            location=self.embedding_location,
            object_storage_credential_name="invalidObjStore_cred"
        )

        # Create vector index object
        async_vector_index = select_ai.AsyncVectorIndex(
            index_name="test_vector_index",
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.async_profile
        )

        with self.assertRaises(oracledb.DatabaseError):
            await async_vector_index.create(replace=True)

    
    async def test_async_create_vector_index_invalid_location(self):
        vector_index_attributes = select_ai.OracleVectorIndexAttributes(
            location="invalid_location",
            object_storage_credential_name=self.objstore_cred
        )

        # Create vector index object
        async_vector_index = select_ai.AsyncVectorIndex(
            index_name="test_vector_index",
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.async_profile
        )

        with self.assertRaises(oracledb.DatabaseError):
            await async_vector_index.create(replace=True)
  
    
    async def test_async_create_vector_index_missing_attributes(self):
        with self.assertRaises(AttributeError):
            await select_ai.AsyncVectorIndex(
                  index_name="test_vector_index",
                  attributes=None,
                  profile=self.async_profile
            ).create()
    
    
    async def test_async_create_vector_index_invalid_attributes_type(self):
        with self.assertRaises(TypeError):
            await select_ai.AsyncVectorIndex(
                index_name="test_vector_index",
                attributes="invalid_attributes",  # invalid type
                profile=self.async_profile
            ).create()

    
    async def test_async_create_vector_index_invalid_name_type(self):
        with self.assertRaises(oracledb.DatabaseError) as cm:
            await select_ai.AsyncVectorIndex(
                index_name=12345,  # invalid type (int instead of str)
                attributes=self.vector_index_attributes,
                profile=self.async_profile
            ).create()

        # Verify error
        self.assertIn("ORA-20048", str(cm.exception))
        self.assertIn("Invalid vector index name", str(cm.exception))
    

    async def test_async_create_vector_index_empty_name(self):
        with self.assertRaises(oracledb.DatabaseError) as cm:
            await select_ai.AsyncVectorIndex(
                index_name="",
                attributes=self.vector_index_attributes,
                profile=self.async_profile
            ).create()

        # Verify the error code/message
        self.assertIn("ORA-20048", str(cm.exception))
        self.assertIn("Missing vector index name", str(cm.exception))
    

    async def test_async_create_vector_index_invalid_profile(self):
        # Create vector index object
        async_vector_index = select_ai.AsyncVectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            description="Test vector index",
            profile="invalid_profile"
        )
        with self.assertRaises(ValueError):
            await async_vector_index.create()

    
    async def test_async_create_vector_index_none_attributes(self):
        async_vector_index = select_ai.AsyncVectorIndex(
            index_name="test_vector_index",
            attributes=None,
            description="Test vector index",
            profile="invalid_profile"
        )
        with self.assertRaises(TypeError):
            await async_vector_index.create()


    # Boundary Cases
    async def test_async_create_vector_index_long_name(self):
        long_name = "X" * 150  # > Oracle identifier length
        async_vector_index = select_ai.AsyncVectorIndex(
            index_name=long_name,
            attributes=self.vector_index_attributes,
            profile=self.async_profile
        )
        with self.assertRaises(oracledb.DatabaseError):
            await async_vector_index.create()
    
    
    async def test_async_create_vector_index_long_description(self):
        long_desc = "D" * 5000  # deliberately too long

        # Create vector index object
        async_vector_index = select_ai.AsyncVectorIndex(
            index_name="test_vector_index",
            attributes=self.vector_index_attributes,
            description=long_desc,
            profile=self.async_profile
        )

        # Expect DatabaseError due to description length
        with self.assertRaises(oracledb.DatabaseError) as cm:
            await async_vector_index.create(replace=True)

        # Verify Oracle error details
        self.assertIn("ORA-20045", str(cm.exception))
        self.assertIn("description is too long", str(cm.exception))

    
    async def test_async_create_vector_index_multiple_recreates(self):
        for _ in range(10):
            await self.async_vector_index.create(replace=True)



if __name__ == "__main__":
    test_env.run_test_cases()
import unittest
import select_ai
import test_env
import oracledb
import os
import asyncio
import re


class TestAsyncListVectorIndex(unittest.IsolatedAsyncioTestCase):
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
    

    async def create_async_vector_index(self, index_name):
        # Specify objects to create an embedding for.
        # The objects reside in ObjectStore and the vector database is Oracle
        vector_index_attributes = select_ai.OracleVectorIndexAttributes(
            location=self.embedding_location,
            object_storage_credential_name=self.objstore_cred
        )

        # Create vector index object
        async_vector_index = select_ai.AsyncVectorIndex(
            index_name=index_name,
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=self.async_profile
        )

        # Create vector index
        await async_vector_index.create(replace=True)


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

        # Create some vector indexes
        self.objstore_cred = "OBJSTORE_CRED"

        self.indexes = [f"test_vector_index{i}" for i in range(1, 6)] + \
            [f"test_vecidx{i}" for i in range(1, 3)]

        for idx in self.indexes:
            try:
                await self.create_async_vector_index(index_name=idx)
            except Exception:
                pass

        self.async_vector_index = select_ai.AsyncVectorIndex()
    
      
    async def asyncTearDown(self):
        # Clean up test indexes and close connection.
        for idx in self.indexes:
            try:
                # Delete Vector Index
                async_vector_index = select_ai.AsyncVectorIndex(index_name_pattern=idx)
                await async_vector_index.delete(force=True)
            except Exception:
                pass

        # Delete Profile
        await self.delete_async_profile()

        # Delete Credentials
        await self.delete_async_credential()

        # Disconnect from DB
        try:
            await select_ai.async_disconnect()
        except Exception as e:
            print(f"Warning: disconnect failed ({e})")


    # ---------- Positive Test Cases ----------
    async def test_async_list_matching_names(self):        
        expected_index_names = [f"test_vector_index{i}".upper() for i in range(1, 6)] + \
                            [f"test_vecidx{i}".upper() for i in range(1, 3)]

        actual_indexes = [idx.index_name async for idx in self.async_vector_index.list(index_name_pattern=".*")]

        # Verify count of indexes
        self.assertEqual(
            len(actual_indexes),
            len(expected_index_names),
            f"Expected {len(expected_index_names)} indexes, got {len(actual_indexes)}"
        )

        # Verify same set of names, ignoring order
        self.assertEqual(
            sorted(actual_indexes),
            sorted(expected_index_names),
            f"Expected names {sorted(expected_index_names)}, got {sorted(actual_indexes)}"
        )
    
    
    async def test_async_list_matching_profile_name(self):
        expected_profile = "vector_ai_profile"
        async for index in self.async_vector_index.list(index_name_pattern=".*"):
            # Verify profile name
            self.assertEqual(
                index.profile.profile_name,
                expected_profile,
                f"Profile mismatch for {index.index_name}: expected {expected_profile}, got {index.profile.profile_name}"
            )


    async def test_async_list_matching_credential_name(self):
        expected_credential = "OBJSTORE_CRED"
        async for index in self.async_vector_index.list(index_name_pattern=".*"):
            # Verify object store credential
            self.assertEqual(
                index.attributes.object_storage_credential_name,
                expected_credential,
                f"Credential mismatch for {index.index_name}: expected {expected_credential}, got {index.attributes.object_storage_credential_name}"
            )
    
    
    async def test_async_list_matching_description(self):
        expected_description = "Test vector index"
        async for index in self.async_vector_index.list(index_name_pattern=".*"):
            # Verify description
            self.assertEqual(
                index.description,
                expected_description,
                f"Description mismatch for {index.index_name}: expected {expected_description}, got {index.description}"
            )


    async def test_async_list_exact_match(self):
        indexes = [idx async for idx in self.async_vector_index.list(index_name_pattern="^test_vector_index1$")]
        self.assertEqual(indexes[0].index_name, "TEST_VECTOR_INDEX1")
    

    async def test_async_list_multiple_matches(self):
        actual_indexes = []
        async for index in self.async_vector_index.list(index_name_pattern="^test_vector_index"):
            actual_indexes.append(index)

        # Verify count
        expected_count = 5
        self.assertEqual(
            len(list(actual_indexes)),
            expected_count,
            f"Expected {expected_count} indexes, got {len(list(actual_indexes))}"
        )

        # Verify each index name
        for i, index in enumerate(actual_indexes, start=1):
            expected_index_name = f"TEST_VECTOR_INDEX{i}"
            self.assertEqual(
                index.index_name,
                expected_index_name,
                f"Index name mismatch: expected {expected_index_name}, got {index.index_name}"
            )


    async def test_async_list_case_sensitive_pattern(self):
        indexes = [idx async for idx in self.async_vector_index.list(index_name_pattern="^TEST_VECTOR_INDEX?")]
        self.assertTrue(any(idx.index_name == "TEST_VECTOR_INDEX2" for idx in indexes))


    async def test_async_list_case_insensitive_pattern(self):
        indexes = []
        async for index in self.async_vector_index.list(index_name_pattern="(?i)^TEST"):
            indexes.append(index)

        # for index in indexes:
        #     print(index.index_name)
        self.assertTrue(any(idx.index_name == "TEST_VECTOR_INDEX1" for idx in indexes))
    

    async def test_async_list_complex_regex_or_operator(self):
        indexes = []
        async for index in self.async_vector_index.list(index_name_pattern="^(test_vector_index|test_vecidx)"):
            indexes.append(index)

        names = [idx.index_name for idx in indexes]
        self.assertIn("TEST_VECTOR_INDEX1", names)
        self.assertIn("TEST_VECIDX1", names)

        # Invalid Index
        self.assertNotIn("INVALID_VECIDX1", names)
    

    # ----- Negative Cases -----
    async def test_async_list_non_matching_pattern(self):
        indexes = []
        async for index in self.async_vector_index.list(index_name_pattern="^xyz"):
            indexes.append(index)

        self.assertEqual(len(list(indexes)), 0)
    

    async def test_async_list_invalid_regex_pattern(self):
        with self.assertRaises(oracledb.DatabaseError) as cm:
            _ = [idx async for idx in self.async_vector_index.list("[unclosed")]

        # Optional: verify the error code/message
        self.assertIn(
            "ORA-12726",
            str(cm.exception),
            f"Expected ORA-12726 error, got {cm.exception}"
        )


    async def test_async_list_invalid_type_pattern(self):
        with self.assertRaises(TypeError):
            _ = [idx async for idx in self.async_vector_index.list(123)]
    

    async def test_async_list_invalid_type_pattern(self):
        # Invalid type -> expect empty list
        indexes = [idx async for idx in self.async_vector_index.list(123)]
        self.assertEqual(
            len(indexes), 0,
            f"Expected 0 indexes for invalid type pattern, got {len(indexes)}"
        )

    # ----- Edge Cases -----
    async def test_async_list_none_pattern_match(self):
        # None should usually mean "match all"
        indexes = [idx async for idx in self.async_vector_index.list(None)]
        self.assertNotEqual(len(indexes), len(self.indexes))

    
    async def test_async_list_empty_string_pattern_matches(self):
        # Empty string should typically return all (but verify)
        indexes = [idx async for idx in self.async_vector_index.list("")]
        self.assertNotEqual(len(indexes), len(self.indexes))

    async def test_async_list_whitespace_pattern(self):
        indexes = [idx async for idx in self.async_vector_index.list(" ")]
        self.assertEqual(len(indexes), 0)

    
    async def test_async_list_numeric_pattern(self):
        indexes = [idx async for idx in self.async_vector_index.list("test123")]
        self.assertEqual(
            len(indexes), 0,
            f"Expected no indexes to match 'test123', but got {len(indexes)}"
        )

    
    async def test_async_list_special_characters_in_pattern(self):
        indexes = [idx async for idx in self.async_vector_index.list("test_vector_index1$")]
        self.assertEqual(len(indexes), 1)

    
    async def test_async_list_long_pattern_no_match(self):
        pattern = "^" + "a" * 1000 + "$"
        with self.assertRaises(oracledb.DatabaseError) as cm:
            _ = [idx async for idx in self.async_vector_index.list(pattern)]
        self.assertIn(
            "ORA-12733", str(cm.exception),
            f"Expected ORA-12733 error, got {cm.exception}"
        )

    
    async def test_async_list_case_insensitive_match(self):
        indexes = [idx async for idx in self.async_vector_index.list("^TEST")]
        self.assertEqual(len(indexes), 7)


if __name__ == "__main__":
    test_env.run_test_cases()
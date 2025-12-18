import unittest
import select_ai
import test_env
import oracledb
import os
import re


class TestListVectorIndex(unittest.TestCase):
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
    def create_vector_index(cls, index_name):
        # Specify objects to create an embedding for.
        # The objects reside in ObjectStore and the vector database is Oracle
        vector_index_attributes = select_ai.OracleVectorIndexAttributes(
            location=cls.embedding_location,
            object_storage_credential_name=cls.objstore_cred
        )

        # Create vector index object
        vector_index = select_ai.VectorIndex(
            index_name=index_name,
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=cls.profile
        )

        # Create vector index
        vector_index.create(replace=True)


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

        cls.objstore_cred = "OBJSTORE_CRED"

        # Create some vector indexes
        cls.indexes = [f"test_vector_index{i}" for i in range(1, 6)] + \
            [f"test_vecidx{i}" for i in range(1, 3)]
        for idx in cls.indexes:
            try:
                cls.create_vector_index(index_name=idx)
            except Exception:
                pass

    
    @classmethod
    def tearDownClass(cls):
        # Clean up test indexes and close connection.
        for idx in cls.indexes:
            try:
                # Delete Vector Index
                vector_index = select_ai.VectorIndex(index_name_pattern=idx)
                vector_index.delete(force=True)
            except Exception:
                pass

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
        self.indexes = self.__class__.indexes
        self.vector_index = select_ai.VectorIndex()


    # ---------- Positive Test Cases ----------
    def test_list_matching_names(self):        
        expected_index_names = [f"test_vector_index{i}".upper() for i in range(1, 6)] + \
                            [f"test_vecidx{i}".upper() for i in range(1, 3)]

        actual_indexes = list(self.vector_index.list(index_name_pattern=".*"))

        # Verify count of indexes
        self.assertEqual(
            len(actual_indexes),
            len(expected_index_names),
            f"Expected {len(expected_index_names)} indexes, got {len(actual_indexes)}"
        )

        # Verify each index name 
        for index, expected_name in zip(actual_indexes, expected_index_names):
            self.assertEqual(
                index.index_name,
                expected_name,
                f"Index name mismatch: expected {expected_name}, got {index.index_name}"
            )
    
    
    def test_list_matching_profile_name(self):
        expected_profile = "vector_ai_profile"
        for index in self.vector_index.list(index_name_pattern=".*"):
            # Verify profile name
            self.assertEqual(
                index.profile.profile_name,
                expected_profile,
                f"Profile mismatch for {index.index_name}: expected {expected_profile}, got {index.profile.profile_name}"
            )


    def test_list_matching_credential_name(self):
        expected_credential = "OBJSTORE_CRED"
        for index in self.vector_index.list(index_name_pattern=".*"):
            # Verify object store credential
            self.assertEqual(
                index.attributes.object_storage_credential_name,
                expected_credential,
                f"Credential mismatch for {index.index_name}: expected {expected_credential}, got {index.attributes.object_storage_credential_name}"
            )
    
    
    def test_list_matching_description(self):
        expected_description = "Test vector index"
        for index in self.vector_index.list(index_name_pattern=".*"):
            # Verify description
            self.assertEqual(
                index.description,
                expected_description,
                f"Description mismatch for {index.index_name}: expected {expected_description}, got {index.description}"
            )


    def test_list_exact_match(self):
        indexes = self.vector_index.list(index_name_pattern="^test_vector_index1$")
        self.assertEqual(list(indexes)[0].index_name, "TEST_VECTOR_INDEX1")
    

    def test_list_multiple_matches(self):
        actual_indexes = list(self.vector_index.list(index_name_pattern="^test_vector_index"))
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


    def test_list_case_sensitive_pattern(self):
        indexes = self.vector_index.list("^TEST_VECTOR_INDEX?")
        self.assertTrue(any(idx.index_name == "TEST_VECTOR_INDEX2" for idx in indexes))


    def test_list_case_insensitive_pattern(self):
        indexes = self.vector_index.list("(?i)^TEST")

        # for index in indexes:
        #     print(index.index_name)
        self.assertTrue(any(idx.index_name == "TEST_VECTOR_INDEX1" for idx in indexes))
    

    def test_list_complex_regex_or_operator(self):
        indexes = self.vector_index.list("^(test_vector_index|test_vecidx)")
        names = [idx.index_name for idx in indexes]
        self.assertIn("TEST_VECTOR_INDEX1", names)
        self.assertIn("TEST_VECIDX1", names)

        # Invalid Index
        self.assertNotIn("INVALID_VECIDX1", names)
    

    # ----- Negative Cases -----
    def test_list_non_matching_pattern(self):
        indexes = self.vector_index.list(index_name_pattern="^xyz")
        self.assertEqual(len(list(indexes)), 0)
    

    def test_list_invalid_regex_pattern(self):
        # Expect Oracle to raise an error for invalid regex
        with self.assertRaises(oracledb.DatabaseError) as cm:
            list(self.vector_index.list("[unclosed"))

        # Optional: verify the error code/message
        self.assertIn("ORA-12726", str(cm.exception), 
                    f"Expected ORA-12726 error, got {cm.exception}")


    # def test_list_invalid_type_pattern(self):
        # with self.assertRaises(TypeError):
        #     self.vector_index.list(123)
    

    def test_list_invalid_type_pattern(self):
        indexes = list(self.vector_index.list(123))

        # Should just return an empty list (no matches)
        self.assertEqual(
            len(indexes), 0,
            f"Expected 0 indexes for invalid type pattern, got {len(indexes)}"
        )

    # ----- Edge Cases -----
    def test_list_none_pattern_match(self):
        indexes = self.vector_index.list(None)
        self.assertNotEqual(len(list(indexes)), len(self.indexes))

    def test_list_empty_string_pattern_matches(self):
        indexes = self.vector_index.list("")
        self.assertNotEqual(len(list(indexes)), len(self.indexes))

    
    def test_list_whitespace_pattern(self):
        indexes = self.vector_index.list(" ")
        self.assertEqual(len(list(indexes)), 0)

    
    def test_list_numeric_pattern(self):
        indexes = list(self.vector_index.list("test123"))

        # Expect no matches, so indexes should be empty
        self.assertEqual(
            len(indexes),
            0,
            f"Expected no indexes to match 'test123', but got {len(indexes)}"
        )

    def test_list_special_characters_in_pattern(self):
        indexes = self.vector_index.list("test_vector_index1$")
        self.assertEqual(len(list(indexes)), 1)

    def test_list_long_pattern_no_match(self):
        pattern = "^" + "a" * 1000 + "$"

        # Expect Oracle to raise regex-too-long error
        with self.assertRaises(oracledb.DatabaseError) as cm:
            list(self.vector_index.list(pattern))

        # Optional: check correct Oracle error code
        self.assertIn("ORA-12733", str(cm.exception),
                    f"Expected ORA-12733 error, got {cm.exception}")


    def test_list_case_insensitive_match(self):
        indexes = self.vector_index.list("^TEST")
        self.assertEqual(len(list(indexes)), 7)


if __name__ == "__main__":
    test_env.run_test_cases()
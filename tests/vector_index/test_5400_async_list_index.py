# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import logging

import oracledb
import pytest
import select_ai
from select_ai import AsyncVectorIndex, OracleVectorIndexAttributes

logger = logging.getLogger("TestAsyncListVectorIndex")

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="class")
def list_vec_params(request, vcidx_params):
    request.cls.list_vec_params = vcidx_params


@pytest.fixture(scope="class", autouse=True)
async def setup_and_teardown(request, async_connect, list_vec_params):
    logger.info("=== Setting up TestAsyncListVectorIndex class ===")
    p = request.cls.list_vec_params

    assert await select_ai.async_is_connected(), "Connection to DB failed"

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
    request.cls.resource_suffix = p["resource_suffix"]
    request.cls.genai_cred = p["genai_cred"]
    request.cls.objstore_cred = p["objstore_cred"]
    request.cls.profile_name = p["profile_name"]

    await request.cls.create_credential()
    request.cls.profile = await request.cls.create_profile()
    logger.info("Profile %s created successfully.", request.cls.profile_name)

    request.cls.indexes = [
        f"{p['list_index_prefix']}{i}" for i in range(1, 6)
    ] + [f"{p['list_vecidx_prefix']}{i}" for i in range(1, 3)]

    for idx in request.cls.indexes:
        try:
            await request.cls.create_vector_index(index_name=idx)
        except Exception as exc:
            logger.warning(
                "Index creation failed or already exists for %s: %s",
                idx,
                exc,
            )

    yield

    logger.info("=== Tearing down TestAsyncListVectorIndex class ===")
    for idx in request.cls.indexes:
        try:
            await AsyncVectorIndex(index_name=idx).delete(force=True)
        except Exception as exc:
            logger.warning("Warning: drop vector index failed: %s", exc)

    try:
        await request.cls.profile.delete()
    except Exception as exc:
        logger.warning("profile.delete() raised %s unexpectedly.", exc)

    await request.cls.delete_credential()
    logger.info("Teardown complete.\n")


@pytest.fixture(autouse=True)
async def log_test_name(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    request.cls.vector_index = AsyncVectorIndex()
    yield
    logger.info("--- Finished test: %s ---", request.function.__name__)


@pytest.mark.usefixtures("list_vec_params", "setup_and_teardown")
class TestAsyncListVectorIndex:
    @staticmethod
    def _managed_index_names(indexes):
        return {index_name.upper() for index_name in indexes}

    @classmethod
    def get_native_cred_param(cls, cred_name=None) -> dict:
        logger.info("Preparing native credential params for: %s", cred_name)
        p = cls.list_vec_params
        return dict(
            credential_name=cred_name,
            user_ocid=p["user_ocid"],
            tenancy_ocid=p["tenancy_ocid"],
            private_key=p["private_key"],
            fingerprint=p["fingerprint"],
        )

    @classmethod
    def get_cred_param(cls, cred_name=None) -> dict:
        logger.info("Preparing basic credential params for: %s", cred_name)
        p = cls.list_vec_params
        return dict(
            credential_name=cred_name,
            username=p["cred_username"],
            password=p["cred_password"],
        )

    @classmethod
    async def create_credential(
        cls,
        genai_cred=None,
        objstore_cred=None,
    ):
        genai_cred = genai_cred or cls.genai_cred
        objstore_cred = objstore_cred or cls.objstore_cred
        logger.info("Creating credentials: %s, %s", genai_cred, objstore_cred)
        p = cls.list_vec_params

        genai_credential = cls.get_native_cred_param(genai_cred)
        await select_ai.async_create_credential(
            credential=genai_credential,
            replace=True,
        )

        if p.get("cred_username") and p.get("cred_password"):
            objstore_credential = cls.get_cred_param(objstore_cred)
            await select_ai.async_create_credential(
                credential=objstore_credential,
                replace=True,
            )
            logger.info("Credentials created.")
        else:
            logger.info(
                "Skipping ObjectStore credential creation "
                "(CRED_USERNAME/CRED_PASSWORD not set)."
            )

    @classmethod
    async def create_profile(cls, profile_name=None):
        p = cls.list_vec_params
        profile_name = profile_name or cls.profile_name
        return await select_ai.AsyncProfile(
            profile_name=profile_name,
            attributes=select_ai.ProfileAttributes(
                credential_name=cls.genai_cred,
                provider=select_ai.OCIGenAIProvider(
                    oci_compartment_id=p["oci_compartment_id"],
                    oci_apiformat="GENERIC",
                    embedding_model="cohere.embed-english-v3.0",
                ),
            ),
            description="OCI GENAI Profile",
            replace=True,
        )

    @classmethod
    async def create_vector_index(cls, index_name):
        logger.info("Creating vector index: %s", index_name)
        vector_index_attributes = OracleVectorIndexAttributes(
            location=cls.list_vec_params["embedding_location"],
            object_storage_credential_name=cls.objstore_cred,
        )
        vector_index = AsyncVectorIndex(
            index_name=index_name,
            attributes=vector_index_attributes,
            description="Test vector index",
            profile=cls.profile,
        )
        await vector_index.create(replace=True)
        logger.info("Vector index '%s' created successfully.", index_name)

    @classmethod
    async def delete_credential(cls):
        try:
            await select_ai.async_delete_credential(cls.genai_cred, force=True)
        except Exception as exc:
            logger.warning("delete_credential() raised %s unexpectedly.", exc)
        try:
            await select_ai.async_delete_credential(
                cls.objstore_cred, force=True
            )
        except Exception as exc:
            logger.warning("delete_credential() raised %s unexpectedly.", exc)

    async def collect_indexes(self, pattern=".*"):
        return [
            idx
            async for idx in self.vector_index.list(index_name_pattern=pattern)
        ]

    def expected_index_names(self):
        return [index_name.upper() for index_name in self.indexes]

    async def fetch_expected_indexes(self):
        return [
            await AsyncVectorIndex.fetch(index_name)
            for index_name in self.expected_index_names()
        ]

    async def test_5401(self):
        """Verify list of vector indexes with matching names."""
        logger.info("Verifying list of vector indexes with matching names...")
        expected_index_names = self.expected_index_names()
        actual_indexes = await self.collect_indexes(".*")
        logger.info(
            "Found %s indexes, verifying names match expectations...",
            len(actual_indexes),
        )
        actual_index_names = [idx.index_name for idx in actual_indexes]
        matched_names = [
            name for name in actual_index_names if name in expected_index_names
        ]
        assert sorted(matched_names) == sorted(expected_index_names), (
            f"Expected names {sorted(expected_index_names)}, "
            f"got {sorted(actual_index_names)}"
        )
        logger.info("All expected index names matched as expected.")

    async def test_5402(self):
        """Verify each index has correct profile name."""
        logger.info("Verifying each index has correct profile name...")
        expected_profile = self.profile_name
        for index in await self.fetch_expected_indexes():
            assert index.profile.profile_name == expected_profile, (
                f"Profile mismatch for {index.index_name}: "
                f"expected {expected_profile}, got {index.profile.profile_name}"
            )
        logger.info("All indexes have correct profile name.")

    async def test_5403(self):
        """Verify each index has correct object store credential name."""
        logger.info(
            "Verifying each index has correct object store credential name..."
        )
        expected_credential = self.objstore_cred
        for index in await self.fetch_expected_indexes():
            assert (
                index.attributes.object_storage_credential_name
                == expected_credential
            ), (
                f"Credential mismatch for {index.index_name}: "
                f"expected {expected_credential}, "
                f"got {index.attributes.object_storage_credential_name}"
            )
        logger.info("All indexes have correct object store credential name.")

    async def test_5404(self):
        """Verify descriptions for all indexes."""
        logger.info("Verifying descriptions for all indexes...")
        expected_description = "Test vector index"
        for index in await self.fetch_expected_indexes():
            assert index.description == expected_description, (
                f"Description mismatch for {index.index_name}: "
                f"expected {expected_description}, got {index.description}"
            )
        logger.info("All indexes have correct descriptions.")

    async def test_5405(self):
        """Test exact match listing for index name."""
        logger.info(
            "Testing exact match listing for index name "
            "'test_vector_index1'..."
        )
        indexes = await self.collect_indexes(f"^{self.indexes[0]}$")
        assert indexes[0].index_name == self.indexes[0].upper()
        logger.info("Exact match returned correct index.")

    async def test_5406(self):
        """Verify multiple matches for pattern."""
        logger.info(
            "Verifying multiple matches for pattern '^test_vector_index'..."
        )
        index_prefix = self.list_vec_params["list_index_prefix"]
        actual_indexes = await self.collect_indexes(f"^{index_prefix}")
        actual_index_names = [index.index_name for index in actual_indexes]
        expected_index_names = [name.upper() for name in self.indexes[:5]]
        matched_names = [
            name for name in actual_index_names if name in expected_index_names
        ]
        assert sorted(matched_names) == sorted(expected_index_names), (
            f"Expected names {sorted(expected_index_names)}, "
            f"got {sorted(actual_index_names)}"
        )
        logger.info("Multiple index names verified successfully.")

    async def test_5407(self):
        """Test case-sensitive regex pattern for listing indexes."""
        logger.info(
            "Testing case-sensitive regex pattern for listing indexes..."
        )
        indexes = await self.collect_indexes("^TEST_VECTOR_INDEX?")
        assert any(
            idx.index_name == self.indexes[1].upper() for idx in indexes
        )
        logger.info("Case-sensitive pattern matched correctly.")

    async def test_5408(self):
        """Test case-insensitive regex pattern for listing indexes."""
        logger.info(
            "Testing case-insensitive regex pattern for listing indexes..."
        )
        indexes = await self.collect_indexes("^TEST")
        assert any(
            idx.index_name.upper() == self.indexes[0].upper()
            for idx in indexes
        )
        logger.info("Case-insensitive pattern matched correctly.")

    async def test_5409(self):
        """Test complex regex pattern with OR operator."""
        logger.info("Testing complex regex pattern with OR operator...")
        list_index_prefix = self.list_vec_params["list_index_prefix"]
        list_vecidx_prefix = self.list_vec_params["list_vecidx_prefix"]
        indexes = await self.collect_indexes(
            f"^({list_index_prefix}|{list_vecidx_prefix})"
        )
        names = [idx.index_name for idx in indexes]
        assert self.indexes[0].upper() in names
        assert self.indexes[5].upper() in names
        assert "INVALID_VECIDX1" not in names
        logger.info("Complex regex OR pattern matched correctly.")

    async def test_5410(self):
        """Test non-matching regex pattern returns nothing."""
        logger.info("Testing non-matching regex pattern...")
        indexes = await self.collect_indexes("^xyz")
        assert len(indexes) == 0
        logger.info("Non-matching pattern returned no results as expected.")

    async def test_5411(self):
        """Test invalid regex pattern expecting ORA-12726 error."""
        logger.info(
            "Testing invalid regex pattern expecting ORA-12726 error..."
        )
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.collect_indexes("[unclosed")
        assert "ORA-12726" in str(exc_info.value)
        logger.info("Invalid regex correctly raised ORA-12726 error.")

    async def test_5412(self):
        """Test invalid type pattern (numeric instead of string)."""
        logger.info(
            "Testing invalid type pattern (numeric instead of string)..."
        )
        indexes = await self.collect_indexes(123)
        assert len(indexes) == 0
        logger.info(
            "Invalid type pattern handled correctly with empty result."
        )

    async def test_5413(self):
        """Explicit None should not behave like the default match-all pattern."""
        logger.info("Testing None as pattern input...")
        indexes = await self.collect_indexes(None)
        actual_index_names = {idx.index_name for idx in indexes}
        managed_index_names = self._managed_index_names(self.indexes)
        assert managed_index_names.isdisjoint(actual_index_names), (
            "Passing None should not fall back to the default '.*' listing "
            "behavior for the managed test indexes."
        )
        logger.info(
            "None pattern did not fall back to the default listing behavior."
        )

    async def test_5414(self):
        """Empty string should not behave like the default match-all pattern."""
        logger.info("Testing empty string as pattern input...")
        indexes = await self.collect_indexes("")
        actual_index_names = {idx.index_name for idx in indexes}
        managed_index_names = self._managed_index_names(self.indexes)
        assert managed_index_names.isdisjoint(actual_index_names), (
            "Passing an empty string should not fall back to the default "
            "'.*' listing behavior for the managed test indexes."
        )
        logger.info(
            "Empty string pattern did not fall back to the default listing behavior."
        )

    async def test_5415(self):
        """Test whitespace-only pattern."""
        logger.info("Testing whitespace-only pattern...")
        indexes = await self.collect_indexes(" ")
        assert len(indexes) == 0
        logger.info("Whitespace pattern correctly returned no matches.")

    async def test_5416(self):
        """Test numeric string pattern yields no matches."""
        logger.info("Testing numeric pattern that should yield no matches...")
        indexes = await self.collect_indexes("test123")
        assert len(indexes) == 0
        logger.info("Numeric pattern correctly returned no matches.")

    async def test_5417(self):
        """Test pattern with special characters '$'."""
        logger.info("Testing pattern with special characters '$'...")
        indexes = await self.collect_indexes(f"{self.indexes[0]}$")
        assert len(indexes) == 1
        logger.info("Special character pattern matched correctly.")

    async def test_5418(self):
        """Test extremely long regex pattern expecting ORA-12733 error."""
        logger.info(
            "Testing extremely long regex pattern expecting ORA-12733 error..."
        )
        pattern = "^" + "a" * 1000 + "$"
        with pytest.raises(oracledb.DatabaseError) as exc_info:
            await self.collect_indexes(pattern)
        assert "ORA-12733" in str(exc_info.value)
        logger.info("Long regex correctly raised ORA-12733 error.")

    async def test_5419(self):
        """Test case-insensitive match for prefix."""
        logger.info("Testing case-insensitive match for prefix '^TEST'...")
        indexes = await self.collect_indexes("^TEST")
        expected_index_names = self.expected_index_names()
        actual_index_names = [idx.index_name for idx in indexes]
        matched_names = [
            name for name in actual_index_names if name in expected_index_names
        ]
        assert sorted(matched_names) == sorted(expected_index_names)
        logger.info("Case-insensitive match returned all expected indexes.")

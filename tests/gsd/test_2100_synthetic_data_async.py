# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
2100 - Synthetic data generation tests (async)
"""

import logging
import uuid

import pytest
import select_ai
from oracledb import DatabaseError
from select_ai import (
    AsyncProfile,
    ProfileAttributes,
    SyntheticDataAttributes,
    SyntheticDataParams,
)

logger = logging.getLogger(__name__)

PROFILE_PREFIX = f"PYSAI_2100_{uuid.uuid4().hex.upper()}"


def _build_attributes(record_count=1, **kwargs):
    logger.debug(
        "Building async synthetic data attributes with record_count=%s and extras=%s",
        record_count,
        kwargs,
    )
    return SyntheticDataAttributes(
        object_name="people",
        record_count=record_count,
        **kwargs,
    )


@pytest.fixture(scope="module")
def async_synthetic_provider(oci_compartment_id):
    return select_ai.OCIGenAIProvider(
        oci_compartment_id=oci_compartment_id,
        oci_apiformat="GENERIC",
    )


@pytest.fixture(scope="module")
def async_synthetic_profile_attributes(
    oci_credential, async_synthetic_provider
):
    return ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        object_list=[
            {"owner": "ADMIN", "name": "people"},
            {"owner": "ADMIN", "name": "gymnast"},
        ],
        provider=async_synthetic_provider,
    )


@pytest.fixture(scope="module")
async def async_synthetic_profile(async_synthetic_profile_attributes):
    logger.info(
        "Creating async synthetic profile %s", f"{PROFILE_PREFIX}_ASYNC"
    )
    profile = await AsyncProfile(
        profile_name=f"{PROFILE_PREFIX}_ASYNC",
        attributes=async_synthetic_profile_attributes,
        description="Synthetic data async test profile",
        replace=True,
    )
    yield profile
    try:
        logger.info(
            "Deleting async synthetic profile %s", profile.profile_name
        )
        await profile.delete(force=True)
    except Exception:
        logger.warning(
            "Failed to delete async synthetic profile %s", profile.profile_name
        )
        pass


@pytest.mark.anyio
async def test_2100_generate_with_full_params(async_synthetic_profile):
    """Generate synthetic data with full parameter set"""
    logger.info(
        "Generating async synthetic data with full params for profile %s",
        async_synthetic_profile.profile_name,
    )
    params = SyntheticDataParams(sample_rows=10, priority="HIGH")
    attributes = _build_attributes(
        record_count=5,
        params=params,
        user_prompt="age must be greater than 20",
    )
    logger.info("Attributes = %s", attributes)
    assert attributes.record_count is 5
    result = await async_synthetic_profile.generate_synthetic_data(attributes)
    assert result is None


@pytest.mark.anyio
async def test_2101_generate_minimum_fields(async_synthetic_profile):
    """Generate synthetic data with minimum fields"""
    logger.info("Generating async synthetic data with minimum fields")
    attributes = _build_attributes()
    logger.info("Attributes = %s", attributes)
    result = await async_synthetic_profile.generate_synthetic_data(attributes)
    assert result is None


@pytest.mark.anyio
async def test_2102_generate_zero_sample_rows(async_synthetic_profile):
    """Generate synthetic data with zero sample rows"""
    logger.info("Generating async synthetic data with zero sample rows")
    params = SyntheticDataParams(sample_rows=0, priority="HIGH")
    attributes = _build_attributes(params=params)
    logger.info("Attributes = %s", attributes)
    assert attributes.params.sample_rows is 0
    result = await async_synthetic_profile.generate_synthetic_data(attributes)
    assert result is None


@pytest.mark.anyio
async def test_2103_generate_single_sample_row(async_synthetic_profile):
    """Generate synthetic data with single sample row"""
    logger.info("Generating async synthetic data with single sample row")
    params = SyntheticDataParams(sample_rows=1, priority="HIGH")
    attributes = _build_attributes(params=params)
    logger.info("Attributes = %s", attributes)
    assert attributes.params.sample_rows is 1
    result = await async_synthetic_profile.generate_synthetic_data(attributes)
    assert result is None


@pytest.mark.anyio
async def test_2104_generate_low_priority(async_synthetic_profile):
    """Generate synthetic data with low priority"""
    logger.info("Generating async synthetic data with low priority")
    params = SyntheticDataParams(sample_rows=1, priority="LOW")
    attributes = _build_attributes(params=params)
    logger.info("Attributes = %s", attributes)
    assert attributes.params.sample_rows is 1
    assert attributes.params.priority is "LOW"
    result = await async_synthetic_profile.generate_synthetic_data(attributes)
    assert result is None


@pytest.mark.anyio
async def test_2105_generate_missing_object_name(async_synthetic_profile):
    """Missing object_name raises error"""
    logger.info("Validating async missing object_name raises error")
    attributes = SyntheticDataAttributes(record_count=1)
    logger.info("Attributes = %s", attributes)
    with pytest.raises(
        ValueError, match="One of object_name and object_list should be set"
    ):
        await async_synthetic_profile.generate_synthetic_data(attributes)


@pytest.mark.anyio
async def test_2106_generate_invalid_priority(async_synthetic_profile):
    """Invalid priority raises error"""
    logger.info("Validating async invalid priority raises error")
    params = SyntheticDataParams(sample_rows=1, priority="CRITICAL")
    attributes = _build_attributes(params=params)
    logger.info("Attributes = %s", attributes)
    with pytest.raises(DatabaseError) as exc_info:
        await async_synthetic_profile.generate_synthetic_data(attributes)
    (error,) = exc_info.value.args
    logger.debug("Error code: %s", error.code)
    logger.debug("Error message:\n%s", error.message)
    assert error.code == 20000
    assert "Invalid value for priority" in error.message


@pytest.mark.anyio
async def test_2107_generate_negative_record_count(async_synthetic_profile):
    """Negative record count raises error"""
    logger.info("Validating async negative record count raises error")
    attributes = _build_attributes(record_count=-5)
    logger.info("Attributes = %s", attributes)
    with pytest.raises(DatabaseError) as exc_info:
        await async_synthetic_profile.generate_synthetic_data(attributes)
    (error,) = exc_info.value.args
    logger.debug("Error code: %s", error.code)
    logger.debug("Error message:\n%s", error.message)
    assert error.code == 20000
    assert "record_count cannot be smaller than 0" in error.message


@pytest.mark.anyio
async def test_2108_generate_with_none_attributes(async_synthetic_profile):
    """Passing None as attributes raises error"""
    logger.info("Validating async None attributes raise error")
    with pytest.raises(
        ValueError, match="'synthetic_data_attributes' cannot be None"
    ):
        await async_synthetic_profile.generate_synthetic_data(None)

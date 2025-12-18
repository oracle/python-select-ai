# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
2100 - Synthetic data generation tests (async)
"""

import uuid

import pytest
import select_ai
from select_ai import (
    AsyncProfile,
    ProfileAttributes,
    SyntheticDataAttributes,
    SyntheticDataParams,
)

PROFILE_PREFIX = f"PYSAI_2100_{uuid.uuid4().hex.upper()}"


def _build_attributes(record_count=1, **kwargs):
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
    profile = await AsyncProfile(
        profile_name=f"{PROFILE_PREFIX}_ASYNC",
        attributes=async_synthetic_profile_attributes,
        description="Synthetic data async test profile",
        replace=True,
    )
    yield profile
    try:
        await profile.delete(force=True)
    except Exception:
        pass


@pytest.mark.anyio
async def test_2100_generate_with_full_params(async_synthetic_profile):
    """Generate synthetic data with full parameter set"""
    params = SyntheticDataParams(sample_rows=10, priority="HIGH")
    attributes = _build_attributes(
        record_count=5,
        params=params,
        user_prompt="age must be greater than 20",
    )
    result = await async_synthetic_profile.generate_synthetic_data(attributes)
    assert result is None


@pytest.mark.anyio
async def test_2101_generate_minimum_fields(async_synthetic_profile):
    """Generate synthetic data with minimum fields"""
    attributes = _build_attributes()
    result = await async_synthetic_profile.generate_synthetic_data(attributes)
    assert result is None


@pytest.mark.anyio
async def test_2102_generate_zero_sample_rows(async_synthetic_profile):
    """Generate synthetic data with zero sample rows"""
    params = SyntheticDataParams(sample_rows=0, priority="HIGH")
    attributes = _build_attributes(params=params)
    result = await async_synthetic_profile.generate_synthetic_data(attributes)
    assert result is None


@pytest.mark.anyio
async def test_2103_generate_single_sample_row(async_synthetic_profile):
    """Generate synthetic data with single sample row"""
    params = SyntheticDataParams(sample_rows=1, priority="HIGH")
    attributes = _build_attributes(params=params)
    result = await async_synthetic_profile.generate_synthetic_data(attributes)
    assert result is None


@pytest.mark.anyio
async def test_2104_generate_low_priority(async_synthetic_profile):
    """Generate synthetic data with low priority"""
    params = SyntheticDataParams(sample_rows=1, priority="LOW")
    attributes = _build_attributes(params=params)
    result = await async_synthetic_profile.generate_synthetic_data(attributes)
    assert result is None


@pytest.mark.anyio
async def test_2105_generate_missing_object_name(async_synthetic_profile):
    """Missing object_name raises error"""
    attributes = SyntheticDataAttributes(record_count=1)
    with pytest.raises(Exception):
        await async_synthetic_profile.generate_synthetic_data(attributes)


@pytest.mark.anyio
async def test_2106_generate_invalid_priority(async_synthetic_profile):
    """Invalid priority raises error"""
    params = SyntheticDataParams(sample_rows=1, priority="CRITICAL")
    attributes = _build_attributes(params=params)
    with pytest.raises(Exception):
        await async_synthetic_profile.generate_synthetic_data(attributes)


@pytest.mark.anyio
async def test_2107_generate_negative_record_count(async_synthetic_profile):
    """Negative record count raises error"""
    attributes = _build_attributes(record_count=-5)
    with pytest.raises(Exception):
        await async_synthetic_profile.generate_synthetic_data(attributes)


@pytest.mark.anyio
async def test_2108_generate_with_none_attributes(async_synthetic_profile):
    """Passing None as attributes raises error"""
    with pytest.raises(Exception):
        await async_synthetic_profile.generate_synthetic_data(None)

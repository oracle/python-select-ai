# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
2000 - Synthetic data generation tests
"""

import logging
import uuid

import pytest
import select_ai
from oracledb import DatabaseError
from select_ai import (
    Profile,
    ProfileAttributes,
    SyntheticDataAttributes,
    SyntheticDataParams,
)

logger = logging.getLogger(__name__)

PROFILE_PREFIX = f"PYSAI_2000_{uuid.uuid4().hex.upper()}"


def _build_attributes(record_count=1, **kwargs):
    logger.debug(
        "Building synthetic data attributes with record_count=%s and extras=%s",
        record_count,
        kwargs,
    )
    return SyntheticDataAttributes(
        object_name="people",
        record_count=record_count,
        **kwargs,
    )


@pytest.fixture(scope="module")
def synthetic_provider(oci_compartment_id):
    return select_ai.OCIGenAIProvider(
        oci_compartment_id=oci_compartment_id,
        oci_apiformat="GENERIC",
    )


@pytest.fixture(scope="module")
def synthetic_profile_attributes(oci_credential, synthetic_provider):
    return ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        object_list=[
            {"owner": "ADMIN", "name": "people"},
            {"owner": "ADMIN", "name": "gymnast"},
        ],
        provider=synthetic_provider,
    )


@pytest.fixture(scope="module")
def synthetic_profile(synthetic_profile_attributes):
    logger.info("Creating synthetic profile %s", f"{PROFILE_PREFIX}_SYNC")
    profile = Profile(
        profile_name=f"{PROFILE_PREFIX}_SYNC",
        attributes=synthetic_profile_attributes,
        description="Synthetic data test profile",
        replace=True,
    )
    yield profile
    try:
        logger.info("Deleting synthetic profile %s", profile.profile_name)
        profile.delete(force=True)
    except Exception:
        logger.warning("Failed to delete profile %s", profile.profile_name)
        pass


def test_2000_generate_with_full_params(synthetic_profile):
    """Generate synthetic data with full parameter set"""
    logger.info(
        "Generating synthetic data with full params for profile %s",
        synthetic_profile.profile_name,
    )
    params = SyntheticDataParams(sample_rows=10, priority="HIGH")
    attributes = _build_attributes(
        record_count=5,
        params=params,
        user_prompt="age must be greater than 20",
    )
    logger.info("Attributes = %s", attributes)
    assert attributes.record_count is 5
    result = synthetic_profile.generate_synthetic_data(attributes)
    assert result is None


def test_2001_generate_minimum_fields(synthetic_profile):
    """Generate synthetic data with minimum fields"""
    logger.info("Generating synthetic data with minimum fields")
    attributes = _build_attributes()
    logger.info("Attributes = %s", attributes)
    result = synthetic_profile.generate_synthetic_data(attributes)
    logger.info("Result = %s", result)
    assert result is None


def test_2002_generate_zero_sample_rows(synthetic_profile):
    """Generate synthetic data with zero sample rows"""
    logger.info("Generating synthetic data with zero sample rows")
    params = SyntheticDataParams(sample_rows=0, priority="HIGH")
    attributes = _build_attributes(params=params)
    logger.info("Attributes = %s", attributes)
    assert attributes.params.sample_rows is 0
    result = synthetic_profile.generate_synthetic_data(attributes)
    logger.info("Result = %s", result)
    assert result is None


def test_2003_generate_single_sample_row(synthetic_profile):
    """Generate synthetic data with single sample row"""
    logger.info("Generating synthetic data with single sample row")
    params = SyntheticDataParams(sample_rows=1, priority="HIGH")
    attributes = _build_attributes(params=params)
    logger.info("Attributes = %s", attributes)
    assert attributes.params.sample_rows is 1
    result = synthetic_profile.generate_synthetic_data(attributes)
    logger.info("Result = %s", result)
    assert result is None


def test_2004_generate_low_priority(synthetic_profile):
    """Generate synthetic data with low priority"""
    logger.info("Generating synthetic data with low priority")
    params = SyntheticDataParams(sample_rows=1, priority="LOW")
    attributes = _build_attributes(params=params)
    logger.info("Attributes = %s", attributes)
    assert attributes.params.sample_rows is 1
    assert attributes.params.priority is "LOW"
    result = synthetic_profile.generate_synthetic_data(attributes)
    logger.info("Result = %s", result)
    assert result is None


def test_2005_generate_missing_object_name(synthetic_profile):
    """Missing object_name raises error"""
    logger.info("Validating missing object_name raises ValueError")
    attributes = SyntheticDataAttributes(record_count=1)
    with pytest.raises(
        ValueError, match="One of object_name and object_list should be set"
    ):
        synthetic_profile.generate_synthetic_data(attributes)


def test_2006_generate_invalid_priority(synthetic_profile):
    """Invalid priority raises error"""
    logger.info("Validating invalid priority raises error")
    params = SyntheticDataParams(sample_rows=1, priority="CRITICAL")
    attributes = _build_attributes(params=params)
    logger.info("Attributes = %s", attributes)
    with pytest.raises(DatabaseError) as exc_info:
        synthetic_profile.generate_synthetic_data(attributes)
    (error,) = exc_info.value.args
    logger.debug("Error code: %s", error.code)
    logger.debug("Error message:\n%s", error.message)
    assert error.code == 20000
    assert "Invalid value for priority" in error.message


def test_2007_generate_negative_record_count(synthetic_profile):
    """Negative record count raises error"""
    logger.info("Validating negative record count raises error")
    attributes = _build_attributes(record_count=-5)
    logger.info("Attributes = %s", attributes)
    with pytest.raises(DatabaseError) as exc_info:
        synthetic_profile.generate_synthetic_data(attributes)
    (error,) = exc_info.value.args
    logger.debug("Error code: %s", error.code)
    logger.debug("Error message:\n%s", error.message)
    assert error.code == 20000
    assert "record_count cannot be smaller than 0" in error.message


def test_2008_generate_with_none_attributes(synthetic_profile):
    """Passing None as attributes raises error"""
    logger.info("Validating None attributes raise ValueError")
    with pytest.raises(
        ValueError, match="'synthetic_data_attributes' cannot be None"
    ):
        synthetic_profile.generate_synthetic_data(None)

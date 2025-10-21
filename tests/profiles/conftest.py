# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import pytest
import select_ai


@pytest.fixture(scope="module")
def provider():
    return select_ai.OCIGenAIProvider(
        region="us-phoenix-1", oci_apiformat="GENERIC"
    )


@pytest.fixture(scope="module")
def profile_attributes(provider, oci_credential):
    return select_ai.ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        object_list=[{"owner": "SH"}],
        provider=provider,
    )


@pytest.fixture(scope="module")
def min_profile_attributes(provider, oci_credential):
    return select_ai.ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        provider=select_ai.OCIGenAIProvider(),
    )

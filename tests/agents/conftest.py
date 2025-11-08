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
        region="us-chicago-1",
        oci_apiformat="GENERIC",
        model="meta.llama-4-maverick-17b-128e-instruct-fp8",
    )


@pytest.fixture(scope="module")
def profile_attributes(provider, oci_credential):
    return select_ai.ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        object_list=[{"owner": "SH"}],
        provider=provider,
    )


@pytest.fixture(scope="module")
def rag_profile_attributes(provider, oci_credential):
    return select_ai.ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        provider=provider,
    )


@pytest.fixture(scope="module")
def vector_index_attributes(provider, oci_credential):
    return select_ai.OracleVectorIndexAttributes(
        object_storage_credential_name=oci_credential["credential_name"],
        location="https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph",
    )

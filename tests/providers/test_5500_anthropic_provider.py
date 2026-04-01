# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import pytest

pytestmark = pytest.mark.provider

PROVIDER_NAME = "anthropic"


@pytest.fixture
def anthropic_profile(provider_profile_factory):
    return provider_profile_factory(PROVIDER_NAME)


def test_5500_anthropic_provider(anthropic_profile):
    profile, prompt = anthropic_profile
    response = profile.narrate(prompt)
    assert isinstance(response, str)
    assert response.strip()


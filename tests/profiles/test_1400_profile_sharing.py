# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import uuid

import pytest
import select_ai
from select_ai import AsyncProfile, Profile
from select_ai.errors import ProfileNotFoundError

PROFILE_NAME = f"PYSAI_1400_{uuid.uuid4().hex.upper()}"


@pytest.fixture(scope="module")
def shared_profile(profile_attributes):
    profile = Profile(
        profile_name=PROFILE_NAME,
        description="Profile sharing test",
        attributes=profile_attributes,
    )
    yield profile
    profile.delete(force=True)


def test_1401_fetch_and_list_shared_profile(
    shared_profile,
    shared_credential_access,
    sharing_user,
    test_env,
):
    profile_name = shared_profile.profile_name.upper()
    owner = test_env.test_user.upper()
    username = sharing_user["username"]

    def fetch_and_list_as_sharing_user():
        try:
            select_ai.disconnect()
            select_ai.connect(**sharing_user["connect_params"])
            fetched = Profile.fetch(profile_name, owner=owner)
            listed = list(Profile.list(f"^{profile_name}$", owner=owner))
            return fetched, listed
        finally:
            select_ai.disconnect()
            select_ai.create_pool(**test_env.connect_params(use_pool=True))

    shared_profile.grant_access(username)
    try:
        fetched, listed = fetch_and_list_as_sharing_user()
        assert fetched.profile_name == profile_name
        assert fetched.owner == owner
        assert [profile.profile_name for profile in listed] == [profile_name]
        assert [profile.owner for profile in listed] == [owner]
    finally:
        shared_profile.revoke_access(username)

    try:
        select_ai.disconnect()
        select_ai.connect(**sharing_user["connect_params"])
        with pytest.raises(ProfileNotFoundError):
            Profile.fetch(profile_name, owner=owner)
        assert not list(Profile.list(f"^{profile_name}$", owner=owner))
    finally:
        select_ai.disconnect()
        select_ai.create_pool(**test_env.connect_params(use_pool=True))


@pytest.mark.anyio
async def test_1402_async_fetch_and_list_shared_profile(
    shared_profile,
    shared_credential_access,
    sharing_user,
    test_env,
):
    profile_name = shared_profile.profile_name.upper()
    owner = test_env.test_user.upper()
    username = sharing_user["username"]
    owner_profile = await AsyncProfile.fetch(profile_name)

    async def fetch_and_list_as_sharing_user():
        try:
            await select_ai.async_disconnect()
            await select_ai.async_connect(**sharing_user["connect_params"])
            fetched = await AsyncProfile.fetch(profile_name, owner=owner)
            listed = [
                profile
                async for profile in AsyncProfile.list(
                    f"^{profile_name}$",
                    owner=owner,
                )
            ]
            return fetched, listed
        finally:
            await select_ai.async_disconnect()
            select_ai.create_pool_async(
                **test_env.connect_params(use_pool=True)
            )

    await owner_profile.grant_access(username)
    try:
        fetched, listed = await fetch_and_list_as_sharing_user()
        assert fetched.profile_name == profile_name
        assert fetched.owner == owner
        assert [profile.profile_name for profile in listed] == [profile_name]
        assert [profile.owner for profile in listed] == [owner]
    finally:
        await owner_profile.revoke_access(username)

    try:
        await select_ai.async_disconnect()
        await select_ai.async_connect(**sharing_user["connect_params"])
        with pytest.raises(ProfileNotFoundError):
            await AsyncProfile.fetch(profile_name, owner=owner)
        listed = [
            profile
            async for profile in AsyncProfile.list(
                f"^{profile_name}$",
                owner=owner,
            )
        ]
        assert not listed
    finally:
        await select_ai.async_disconnect()
        select_ai.create_pool_async(**test_env.connect_params(use_pool=True))

from typing import Mapping

from .async_profile import AsyncProfile
from .profile import Profile


class Session:
    """Session lets you persist request parameters across DBMS_CLOUD_AI
    requests. This is useful in context-aware conversations
    """

    def __init__(self, profile: Profile, params: Mapping):
        """

        :param profile: An AI Profile to use in this session
        :param params: Parameters to be persisted across requests
        """
        self.params = params
        self.profile = profile

    def chat(self, prompt: str):
        # params = {"conversation_id": self.conversation_id}
        return self.profile.chat(prompt=prompt, params=self.params)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class AsyncSession:
    """AsyncSession lets you persist request parameters across DBMS_CLOUD_AI
    requests. This is useful in context-aware conversations
    """

    def __init__(self, async_profile: AsyncProfile, params: Mapping):
        """

        :param async_profile: An AI Profile to use in this session
        :param params: Parameters to be persisted across requests
        """
        self.params = params
        self.async_profile = async_profile

    async def chat(self, prompt: str):
        return await self.async_profile.chat(prompt=prompt, params=self.params)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

import json
from abc import ABC
from dataclasses import dataclass
from typing import List, Mapping, Optional

import oracledb

from select_ai._abc import SelectAIDataClass
from select_ai.provider import Provider


@dataclass
class ProfileAttributes(SelectAIDataClass):
    """ """

    comments: Optional[bool] = None
    conversation: Optional[str] = None
    credential_name: Optional[str] = None
    max_tokens: Optional[int] = 1024
    object_list: Optional[List[Mapping]] = None
    stop_tokens: Optional[str] = None
    temperature: Optional[float] = None
    vector_index_name: Optional[str] = None
    annotations: Optional[str] = None
    constraints: Optional[str] = None
    case_sensitive_values: Optional[bool] = None
    object_list_mode: Optional[bool] = None
    enforce_object_list: Optional[bool] = None
    enable_sources: Optional[bool] = None
    enable_source_offsets: Optional[bool] = None
    seed: Optional[str] = None
    streaming: Optional[str] = None
    provider: Optional[Provider] = None

    def json(self, exclude_null=True):
        attributes = {}
        for k, v in self.dict(exclude_null=exclude_null).items():
            if isinstance(v, Provider):
                for provider_k, provider_v in v.dict(
                    exclude_null=exclude_null
                ).items():
                    attributes[provider_k] = provider_v
            else:
                attributes[k] = v
        return json.dumps(attributes)

    @classmethod
    def create(cls, **kwargs):
        provider_attributes = {}
        profile_attributes = {}
        for k, v in kwargs.items():
            if isinstance(v, oracledb.LOB):
                v = v.read()
            if k in Provider.keys():
                provider_attributes[k] = v
            else:
                profile_attributes[k] = v
        provider = Provider.create(**provider_attributes)
        profile_attributes["provider"] = provider
        return ProfileAttributes(**profile_attributes)

    @classmethod
    async def async_create(cls, **kwargs):
        provider_attributes = {}
        profile_attributes = {}
        for k, v in kwargs.items():
            if isinstance(v, oracledb.AsyncLOB):
                v = await v.read()
                if k in Provider.keys():
                    provider_attributes[k] = v
                else:
                    profile_attributes[k] = v
        provider = Provider.create(**provider_attributes)
        profile_attributes["provider"] = provider
        return ProfileAttributes(**profile_attributes)

    def set_attribute(self, key, value):
        if key in Provider.keys() and not isinstance(value, Provider):
            setattr(self.provider, key, value)
        else:
            setattr(self, key, value)


class BaseProfile(ABC):
    """
    BaseProfile is an abstract base class representing a Profile
    for Select AI's interactions with AI service providers (LLMs).
    Use either select_ai.Profile or select_ai.AsyncProfile to
    instantiate an AI profile object.
    """

    def __init__(
        self,
        profile_name: Optional[str] = None,
        attributes: Optional[ProfileAttributes] = None,
        description: Optional[str] = None,
        merge: Optional[bool] = False,
        replace: Optional[bool] = False,
    ):
        """Initialize a base profile

        :param str profile_name (optional): Name of the profile

        :param select_ai.provider.ProviderAttributes attributes (optional):
        Object specifying AI profile attributes

        :param str description (optional): Description of the profile

        :param bool merge: Fetches the profile
        from database, merges the attributes and saves it back
        in the database. Default value is False

        :param bool replace: Replaces the profile and attributes
        in the database. Default value is False
        """
        self.profile_name = profile_name
        self.attributes = attributes
        self.description = description
        self.merge = merge
        self.replace = replace

    def __repr__(self):
        return (
            f"Profile(profile_name={self.profile_name}, "
            f"attributes={self.attributes})"
        )

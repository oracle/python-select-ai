from abc import ABC
from dataclasses import dataclass, fields
from typing import Optional

__all__ = ["BaseProfile", "SelectAIDataClass"]


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
        attributes: Optional["select_ai.provider.ProviderAttributes"] = None,
        description: Optional[str] = None,
        fetch_and_merge_attributes: Optional[bool] = False,
        replace: Optional[bool] = True,
    ):
        """Initialize a base profile

        :param str profile_name (optional): Name of the profile

        :param select_ai.provider.ProviderAttributes attributes (optional):
        ProviderAttributes

        :param str description (optional): Description of the profile

        :param bool fetch_and_merge_attributes: Fetches the profile
        from database, merges the attributes and saves it back
        in the database. Default value is False

        :param bool replace: Replaces the profile and attributes
        in the database. Default value is True
        """
        self.profile_name = profile_name
        self.attributes = attributes
        self.description = description
        self.fetch_and_merge_attributes = fetch_and_merge_attributes
        self.replace = replace

    def __repr__(self):
        return (
            f"Profile(profile_name={self.profile_name}, "
            f"attributes={self.attributes})"
        )


@dataclass
class SelectAIDataClass(ABC):

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def keys(self):
        return [field.name for field in fields(self)]

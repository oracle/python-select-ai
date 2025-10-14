# ------------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import json
from abc import ABC
from dataclasses import dataclass
from typing import (
    Any,
    AsyncGenerator,
    Iterator,
    List,
    Mapping,
    Optional,
    Union,
)

import oracledb

from select_ai import BaseProfile
from select_ai._abc import SelectAIDataClass
from select_ai._enums import StrEnum
from select_ai.agent.sql import (
    GET_USER_AI_AGENT,
    GET_USER_AI_AGENT_ATTRIBUTES,
    LIST_USER_AI_AGENTS,
)
from select_ai.async_profile import AsyncProfile
from select_ai.db import async_cursor, cursor
from select_ai.errors import AgentNotFoundError
from select_ai.profile import Profile


@dataclass
class AgentAttributes(SelectAIDataClass):
    """AI Agent Attributes

    :param str profile_name: Name of the AI Profile which agent will
     use to send request to LLM
    :param str role: Agent's role also sent to LLM
    :param bool enable_human_tool: Enable human tool support. Agent
     will ask question to the user for any clarification
    """

    profile_name: str
    role: str
    enable_human_tool: Optional[bool] = True


class BaseAgent(ABC):

    def __init__(
        self,
        agent_name: Optional[str] = None,
        description: Optional[str] = None,
        attributes: Optional[AgentAttributes] = None,
    ):
        if attributes is not None and not isinstance(
            attributes, AgentAttributes
        ):
            raise TypeError(
                "attributes must be an object of type "
                "select_ai.agent.AgentAttributes"
            )
        self.agent_name = agent_name
        self.description = description
        self.attributes = attributes

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"agent_name={self.agent_name}, "
            f"attributes={self.attributes}, description={self.description})"
        )


class Agent(BaseAgent):
    """
    select_ai.agent.Agent class lets you create, delete, enable, disable
    and list AI agents

    :param str agent_name: The name of the AI Agent
    :param str description: Optional description of the AI agent
    :param select_ai.agent.AgentAttributes attributes: AI agent attributes

    """

    @staticmethod
    def _get_attributes(agent_name: str) -> AgentAttributes:
        with cursor() as cr:
            cr.execute(GET_USER_AI_AGENT, agent_name=agent_name.upper())
            attributes = cr.fetchall()
            if attributes:
                post_processed_attributes = {}
                for k, v in attributes:
                    if isinstance(v, oracledb.LOB):
                        post_processed_attributes[k] = v.read()
                    else:
                        post_processed_attributes[k] = v
                return AgentAttributes(**post_processed_attributes)
            else:
                raise AgentNotFoundError(agent_name=agent_name)

    def create(
        self, enabled: Optional[bool] = True, replace: Optional[bool] = False
    ):
        """
        Register a new AI Agent within the Select AI framework

        :param bool enabled: Whether the AI Agent should be enabled.
         Default value is True.

        :param bool replace: Whether the AI Agent should be replaced.
         Default value is False.

        """
        if self.agent_name is None:
            raise AttributeError("Agent must have a name")
        if self.attributes is None:
            raise AttributeError("Agent must have attributes")

        parameters = {
            "agent_name": self.agent_name,
            "attributes": self.attributes.json(),
        }
        if self.description:
            parameters["description"] = self.description

        if not enabled:
            parameters["status"] = "disabled"

        with cursor() as cr:
            try:
                cr.callproc(
                    "DBMS_CLOUD_AI_AGENT.CREATE_AGENT",
                    keyword_parameters=parameters,
                )
            except oracledb.Error as err:
                (err_obj,) = err.args
                if err_obj.code in (20050, 20052) and replace:
                    self.delete(force=True)
                    cr.callproc(
                        "DBMS_CLOUD_AI_AGENT.CREATE_AGENT",
                        keyword_parameters=parameters,
                    )
                else:
                    raise

    def delete(self, force: Optional[bool] = False):
        """
        Delete AI Agent from the database

        :param bool force: Force the deletion. Default value is False.

        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI_AGENT.DROP_AGENT",
                keyword_parameters={
                    "agent_name": self.agent_name,
                    "force": force,
                },
            )

    def disable(self):
        """
        Disable AI Agent

        """
        pass

    def enable(self):
        """
        Enable AI Agent
        """
        pass

    @classmethod
    def fetch(cls, agent_name: str) -> "Agent":
        """
        Fetch AI Agent attributes from the Database and build a proxy object in
        the Python layer

        :param str agent_name: The name of the AI Agent

        :return: select_ai.agent.Agent

        :raises select_ai.errors.AgentNotFoundError:
         If the AI Agent is not found

        """
        pass

    @classmethod
    def list(
        cls, agent_name_pattern: Optional[str] = ".*"
    ) -> Iterator["Agent"]:
        """
        List AI agents matching a pattern

        :param str agent_name_pattern: Regular expressions can be used
         to specify a pattern. Function REGEXP_LIKE is used to perform the
         match. Default value is ".*" i.e. match all agent names.

        :return: Iterator[Agent]
        """
        with cursor() as cr:
            cr.execute(
                LIST_USER_AI_AGENTS,
                agent_name_pattern=agent_name_pattern,
            )
            for row in cr.fetchall():
                agent_name = row[0]
                if row[1]:
                    description = row[1].read()  # Oracle.LOB
                else:
                    description = None
                attributes = cls._get_attributes(agent_name=agent_name)
                yield cls(
                    agent_name=agent_name,
                    description=description,
                    attributes=attributes,
                )

    def set_attributes(self, attributes: AgentAttributes) -> None:
        """
        Set AI Agent attributes
        """
        pass

    def set_attribute(self, attribute_name: str, attribute_value: Any) -> None:
        pass

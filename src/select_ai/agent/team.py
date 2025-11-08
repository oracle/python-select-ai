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
    GET_USER_AI_AGENT_TEAM,
    GET_USER_AI_AGENT_TEAM_ATTRIBUTES,
    LIST_USER_AI_AGENT_TEAMS,
)
from select_ai.async_profile import AsyncProfile
from select_ai.db import async_cursor, cursor
from select_ai.errors import AgentTeamNotFoundError
from select_ai.profile import Profile


@dataclass
class TeamAttributes(SelectAIDataClass):
    """
    AI agent team attributes

    :param List[Mapping] agents: A List of Python dictionaries, each defining
     the agent and the task name. [{"name": "<agent_name>",
     "task": "<task_name>"}]

    :param str process: Execution order of tasks. Currently only "sequential"
     is supported.

    """

    agents: List[Mapping]
    process: str = "sequential"


class BaseTeam(ABC):

    def __init__(
        self,
        team_name: str,
        attributes: TeamAttributes,
        description: Optional[str] = None,
    ):
        if not isinstance(attributes, TeamAttributes):
            raise TypeError(
                f"attributes must be an object of type  "
                f"select_ai.agent.TeamAttributes instance"
            )
        self.team_name = team_name
        self.description = description
        self.attributes = attributes

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"team_name={self.team_name}, "
            f"attributes={self.attributes}, description={self.description})"
        )


class Team(BaseTeam):
    """
    A Team of AI agents work together to accomplish tasks
    select_ai.agent.Team class lets you create, delete, enable, disable and
    list AI Tasks.

    :param str team_name: The name of the AI team
    :param str description: Optional description of the AI team
    :param select_ai.agent.TeamAttributes attributes: AI team attributes

    """

    @staticmethod
    def _get_attributes(team_name: str) -> TeamAttributes:
        with cursor() as cr:
            cr.execute(
                GET_USER_AI_AGENT_TEAM_ATTRIBUTES, team_name=team_name.upper()
            )
            attributes = cr.fetchall()
            if attributes:
                post_processed_attributes = {}
                for k, v in attributes:
                    if isinstance(v, oracledb.LOB):
                        post_processed_attributes[k] = v.read()
                    else:
                        post_processed_attributes[k] = v
                return TeamAttributes(**post_processed_attributes)
            else:
                raise AgentTeamNotFoundError(team_name=team_name)

    @staticmethod
    def _get_description(team_name: str) -> Union[str, None]:
        with cursor() as cr:
            cr.execute(GET_USER_AI_AGENT_TEAM, team_name=team_name.upper())
            team = cr.fetchone()
            if team:
                if team[1] is not None:
                    return team[1].read()
                else:
                    return None
            else:
                raise AgentTeamNotFoundError(team_name=team_name)

    def create(
        self, enabled: Optional[bool] = True, replace: Optional[bool] = False
    ):
        """
        Create a team of AI agents that work together to accomplish tasks.

        :param bool enabled: Whether the AI agent team should be enabled.
         Default value is True.

        :param bool replace: Whether the AI agent team should be replaced.
         Default value is False.

        """
        if self.team_name is None:
            raise AttributeError("Team must have a name")
        if self.attributes is None:
            raise AttributeError("Team must have attributes")

        parameters = {
            "team_name": self.team_name,
            "attributes": self.attributes.json(),
        }
        if self.description:
            parameters["description"] = self.description

        if not enabled:
            parameters["status"] = "disabled"

        with cursor() as cr:
            try:
                cr.callproc(
                    "DBMS_CLOUD_AI_AGENT.CREATE_TEAM",
                    keyword_parameters=parameters,
                )
            except oracledb.Error as err:
                (err_obj,) = err.args
                if err_obj.code in (20053, 20052) and replace:
                    self.delete(force=True)
                    cr.callproc(
                        "DBMS_CLOUD_AI_AGENT.CREATE_TEAM",
                        keyword_parameters=parameters,
                    )
                else:
                    raise

    def delete(self, force: Optional[bool] = False):
        """
        Delete an AI agent team from the database

        :param bool force: Force the deletion. Default value is False.
        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI_AGENT.DROP_TEAM",
                keyword_parameters={
                    "team_name": self.team_name,
                    "force": force,
                },
            )

    def disable(self):
        """
        Disable the AI agent team
        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI_AGENT.DISABLE_TEAM",
                keyword_parameters={
                    "team_name": self.team_name,
                },
            )

    def enable(self):
        """
        Enable the AI agent team
        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI_AGENT.ENABLE_TEAM",
                keyword_parameters={
                    "team_name": self.team_name,
                },
            )

    @classmethod
    def fetch(cls, team_name: str) -> "Team":
        """
        Fetch AI Team attributes from the Database and build a proxy object in
        the Python layer

        :param str team_name: The name of the AI Team

        :return: select_ai.agent.Team

        :raises select_ai.errors.AgentTeamNotFoundError:
         If the AI Team is not found
        """
        attributes = cls._get_attributes(team_name)
        description = cls._get_description(team_name)
        return cls(
            team_name=team_name,
            attributes=attributes,
            description=description,
        )

    @classmethod
    def list(cls, team_name_pattern: Optional[str] = ".*") -> Iterator["Team"]:
        """
        List AI Agent Teams

        :param str team_name_pattern: Regular expressions can be used
         to specify a pattern. Function REGEXP_LIKE is used to perform the
         match. Default value is ".*" i.e. match all teams.

        :return: Iterator[Team]

        """
        with cursor() as cr:
            cr.execute(
                LIST_USER_AI_AGENT_TEAMS,
                team_name_pattern=team_name_pattern,
            )
            for row in cr.fetchall():
                team_name = row[0]
                if row[1]:
                    description = row[1].read()  # Oracle.LOB
                else:
                    description = None
                attributes = cls._get_attributes(team_name=team_name)
                yield cls(
                    team_name=team_name,
                    description=description,
                    attributes=attributes,
                )

    def run(self, prompt: str = None, params: Mapping = None):
        """
        Start a new AI agent team or resume a paused one that is waiting
        for human input. If you provide an existing process ID and the
        associated team process is in the WAITING_FOR_HUMAN state, the
        function resumes the workflow using the input you provide as
        the human response

        :param str prompt: Optional prompt for the user. If the task is
         in the RUNNING state, the input acts as a placeholder for the
         {query} in the task instruction. If the task is in the
         WAITING_FOR_HUMAN state, the input serves as the human response.

        :param Mapping[str, str] params: Optional parameters for the task.
         Currently, the following parameters are supported:

         - conversation_id: Identifies the conversation session associated
         with the agent team

         - variables: key-value pairs that provide additional input to the agent team.

        """
        parameters = {
            "team_name": self.team_name,
        }
        if prompt:
            parameters["user_prompt"] = prompt
        if params:
            parameters["params"] = json.dumps(params)

        with cursor() as cr:
            data = cr.callfunc(
                "DBMS_CLOUD_AI_AGENT.RUN_TEAM",
                oracledb.DB_TYPE_CLOB,
                keyword_parameters=parameters,
            )
            if data is not None:
                result = data.read()
            else:
                result = None
            return result

    def set_attributes(self, attributes: TeamAttributes) -> None:
        """
        Set the attributes of the AI Agent team
        """
        parameters = {
            "object_name": self.team_name,
            "object_type": "team",
            "attributes": attributes.json(),
        }
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI_AGENT.SET_ATTRIBUTES",
                keyword_parameters=parameters,
            )

    def set_attribute(self, attribute_name: str, attribute_value: Any) -> None:
        """
        Set the attribute of the AI Agent team specified by
        `attribute_name` and `attribute_value`.
        """
        parameters = {
            "object_name": self.team_name,
            "object_type": "team",
            "attribute_name": attribute_name,
            "attribute_value": attribute_value,
        }
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI_AGENT.SET_ATTRIBUTE",
                keyword_parameters=parameters,
            )


class AsyncTeam(BaseTeam):
    """
    A Team of AI agents work together to accomplish tasks
    select_ai.agent.Team class lets you create, delete, enable, disable and
    list AI Tasks.

    :param str team_name: The name of the AI team
    :param str description: Optional description of the AI team
    :param select_ai.agent.TeamAttributes attributes: AI team attributes

    """

    @staticmethod
    async def _get_attributes(team_name: str) -> TeamAttributes:
        async with async_cursor() as cr:
            await cr.execute(
                GET_USER_AI_AGENT_TEAM_ATTRIBUTES, team_name=team_name.upper()
            )
            attributes = await cr.fetchall()
            if attributes:
                post_processed_attributes = {}
                for k, v in attributes:
                    if isinstance(v, oracledb.AsyncLOB):
                        post_processed_attributes[k] = await v.read()
                    else:
                        post_processed_attributes[k] = v
                return TeamAttributes(**post_processed_attributes)
            else:
                raise AgentTeamNotFoundError(team_name=team_name)

    @staticmethod
    async def _get_description(team_name: str) -> Union[str, None]:
        async with async_cursor() as cr:
            await cr.execute(
                GET_USER_AI_AGENT_TEAM, team_name=team_name.upper()
            )
            team = await cr.fetchone()
            if team:
                if team[1] is not None:
                    return await team[1].read()
                else:
                    return None
            else:
                raise AgentTeamNotFoundError(team_name=team_name)

    async def create(
        self, enabled: Optional[bool] = True, replace: Optional[bool] = False
    ):
        """
        Create a team of AI agents that work together to accomplish tasks.

        :param bool enabled: Whether the AI agent team should be enabled.
         Default value is True.

        :param bool replace: Whether the AI agent team should be replaced.
         Default value is False.

        """
        if self.team_name is None:
            raise AttributeError("Team must have a name")
        if self.attributes is None:
            raise AttributeError("Team must have attributes")

        parameters = {
            "team_name": self.team_name,
            "attributes": self.attributes.json(),
        }
        if self.description:
            parameters["description"] = self.description

        if not enabled:
            parameters["status"] = "disabled"

        async with async_cursor() as cr:
            try:
                await cr.callproc(
                    "DBMS_CLOUD_AI_AGENT.CREATE_TEAM",
                    keyword_parameters=parameters,
                )
            except oracledb.Error as err:
                (err_obj,) = err.args
                if err_obj.code in (20053, 20052) and replace:
                    await self.delete(force=True)
                    await cr.callproc(
                        "DBMS_CLOUD_AI_AGENT.CREATE_TEAM",
                        keyword_parameters=parameters,
                    )
                else:
                    raise

    async def delete(self, force: Optional[bool] = False):
        """
        Delete an AI agent team from the database

        :param bool force: Force the deletion. Default value is False.
        """
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI_AGENT.DROP_TEAM",
                keyword_parameters={
                    "team_name": self.team_name,
                    "force": force,
                },
            )

    async def disable(self):
        """
        Disable the AI agent team
        """
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI_AGENT.DISABLE_TEAM",
                keyword_parameters={
                    "team_name": self.team_name,
                },
            )

    async def enable(self):
        """
        Enable the AI agent team
        """
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI_AGENT.ENABLE_TEAM",
                keyword_parameters={
                    "team_name": self.team_name,
                },
            )

    @classmethod
    async def fetch(cls, team_name: str) -> "AsyncTeam":
        """
        Fetch AI Team attributes from the Database and build a proxy object in
        the Python layer

        :param str team_name: The name of the AI Team

        :return: select_ai.agent.Team

        :raises select_ai.errors.AgentTeamNotFoundError:
         If the AI Team is not found
        """
        attributes = await cls._get_attributes(team_name)
        description = await cls._get_description(team_name)
        return cls(
            team_name=team_name,
            attributes=attributes,
            description=description,
        )

    @classmethod
    async def list(
        cls, team_name_pattern: Optional[str] = ".*"
    ) -> AsyncGenerator["AsyncTeam", None]:
        """
        List AI Agent Teams

        :param str team_name_pattern: Regular expressions can be used
         to specify a pattern. Function REGEXP_LIKE is used to perform the
         match. Default value is ".*" i.e. match all teams.

        :return: Iterator[Team]

        """
        async with async_cursor() as cr:
            await cr.execute(
                LIST_USER_AI_AGENT_TEAMS,
                team_name_pattern=team_name_pattern,
            )
            rows = await cr.fetchall()
            for row in rows:
                team_name = row[0]
                if row[1]:
                    description = await row[1].read()  # Oracle.AsyncLOB
                else:
                    description = None
                attributes = await cls._get_attributes(team_name=team_name)
                yield cls(
                    team_name=team_name,
                    description=description,
                    attributes=attributes,
                )

    async def run(self, prompt: str = None, params: Mapping = None):
        """
        Start a new AI agent team or resume a paused one that is waiting
        for human input. If you provide an existing process ID and the
        associated team process is in the WAITING_FOR_HUMAN state, the
        function resumes the workflow using the input you provide as
        the human response

        :param str prompt: Optional prompt for the user. If the task is
         in the RUNNING state, the input acts as a placeholder for the
         {query} in the task instruction. If the task is in the
         WAITING_FOR_HUMAN state, the input serves as the human response.

        :param Mapping[str, str] params: Optional parameters for the task.
         Currently, the following parameters are supported:

         - conversation_id: Identifies the conversation session associated
         with the agent team

         - variables: key-value pairs that provide additional input to the agent team.

        """
        parameters = {
            "team_name": self.team_name,
        }
        if prompt:
            parameters["user_prompt"] = prompt
        if params:
            parameters["params"] = json.dumps(params)

        async with async_cursor() as cr:
            data = await cr.callfunc(
                "DBMS_CLOUD_AI_AGENT.RUN_TEAM",
                oracledb.DB_TYPE_CLOB,
                keyword_parameters=parameters,
            )
            if data is not None:
                result = await data.read()
            else:
                result = None
            return result

    async def set_attributes(self, attributes: TeamAttributes) -> None:
        """
        Set the attributes of the AI Agent team
        """
        parameters = {
            "object_name": self.team_name,
            "object_type": "team",
            "attributes": attributes.json(),
        }
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI_AGENT.SET_ATTRIBUTES",
                keyword_parameters=parameters,
            )

    async def set_attribute(
        self, attribute_name: str, attribute_value: Any
    ) -> None:
        """
        Set the attribute of the AI Agent team specified by
        `attribute_name` and `attribute_value`.
        """
        parameters = {
            "object_name": self.team_name,
            "object_type": "team",
            "attribute_name": attribute_name,
            "attribute_value": attribute_value,
        }
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI_AGENT.SET_ATTRIBUTE",
                keyword_parameters=parameters,
            )

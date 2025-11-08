# -----------------------------------------------------------------------------
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
    GET_USER_AI_AGENT_TOOL,
    GET_USER_AI_AGENT_TOOL_ATTRIBUTES,
    LIST_USER_AI_AGENT_TOOLS,
)
from select_ai.async_profile import AsyncProfile
from select_ai.db import async_cursor, cursor
from select_ai.errors import AgentToolNotFoundError
from select_ai.profile import Profile


class NotificationType(StrEnum):
    """
    Notification Types
    """

    SLACK = "slack"
    EMAIL = "email"


class ToolType(StrEnum):
    """
    Built-in Tool Types
    """

    EMAIL = "EMAIL"
    HUMAN = "HUMAN"
    HTTP = "HTTP"
    RAG = "RAG"
    SQL = "SQL"
    SLACK = "SLACK"
    WEBSEARCH = "WEBSEARCH"


@dataclass
class ToolParams(SelectAIDataClass):
    """
    Parameters to register a built-in Tool

    :param str credential_name: Used by SLACK, EMAIL and WEBSEARCH tools

    :param str endpoint: Send HTTP requests to this endpoint

    :param select_ai.agent.NotificationType: Either SLACK or EMAIL

    :param str profile_name: Name of AI profile to use

    :param str recipient: Recipient used for EMAIL notification

    :param str sender: Sender used for EMAIL notification

    :param str slack_channel: Slack channel to use

    :param str smtp_host: SMTP host to use for EMAIL notification

    """

    _REQUIRED_FIELDS: Optional[List] = None

    credential_name: Optional[str] = None
    endpoint: Optional[str] = None
    notification_type: Optional[NotificationType] = None
    profile_name: Optional[str] = None
    recipient: Optional[str] = None
    sender: Optional[str] = None
    slack_channel: Optional[str] = None
    smtp_host: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self._REQUIRED_FIELDS:
            for field in self._REQUIRED_FIELDS:
                if getattr(self, field) is None:
                    raise AttributeError(
                        "Required field '{}' not found.".format(field)
                    )

    @classmethod
    def create(cls, *, tool_type: Optional[ToolType] = None, **kwargs):
        tool_params_cls = ToolTypeParams.get(tool_type, ToolParams)
        return tool_params_cls(**kwargs)

    @classmethod
    def keys(cls):
        return {
            "credential_name",
            "endpoint",
            "notification_type",
            "profile_name",
            "recipient",
            "sender",
            "slack_channel",
            "smtp_host",
        }


@dataclass
class SQLToolParams(ToolParams):

    _REQUIRED_FIELDS = ["profile_name"]


@dataclass
class RAGToolParams(ToolParams):

    _REQUIRED_FIELDS = ["profile_name"]


@dataclass
class SlackNotificationToolParams(ToolParams):

    _REQUIRED_FIELDS = ["credential_name", "slack_channel"]
    notification_type: NotificationType = NotificationType.SLACK


@dataclass
class EmailNotificationToolParams(ToolParams):

    _REQUIRED_FIELDS = ["credential_name", "recipient", "sender", "smtp_host"]
    notification_type: NotificationType = NotificationType.EMAIL


@dataclass
class WebSearchToolParams(ToolParams):

    _REQUIRED_FIELDS = ["credential_name"]


@dataclass
class HumanToolParams(ToolParams):
    pass


@dataclass
class HTTPToolParams(ToolParams):

    _REQUIRED_FIELDS = ["credential_name", "endpoint"]


@dataclass
class ToolAttributes(SelectAIDataClass):
    """
    AI Tool attributes

    :param str instruction: Statement that describes what the tool
     should accomplish and how to do it. This text is included
     in the prompt sent to the LLM.
    :param function: Specifies the PL/SQL procedure or
     function to call when the tool is used
    :param select_ai.agent.ToolParams tool_params: Tool parameters
     for built-in tools
    :param List[Mapping] tool_inputs: Describes input arguments.
     Similar to column comments in a table. For example:
     "tool_inputs": [
       {
         "name": "data_guard",
         "description": "Only supported values are "Enabled" and "Disabled""
       }
     ]

    """

    instruction: Optional[str] = None
    function: Optional[str] = None
    tool_params: Optional[ToolParams] = None
    tool_inputs: Optional[List[Mapping]] = None
    tool_type: Optional[ToolType] = None

    def dict(self, exclude_null=True):
        attributes = {}
        for k, v in self.__dict__.items():
            if v is not None or not exclude_null:
                if isinstance(v, ToolParams):
                    attributes[k] = v.dict(exclude_null=exclude_null)
                else:
                    attributes[k] = v
        return attributes

    @classmethod
    def create(cls, **kwargs):
        tool_attributes = {}
        tool_params = {}
        for k, v in kwargs.items():
            if isinstance(v, oracledb.LOB):
                v = v.read()
            if k in ToolParams.keys():
                tool_params[k] = v
            elif k == "tool_params" and v is not None:
                tool_params = json.loads(v)
            else:
                tool_attributes[k] = v
        tool_params = ToolParams.create(
            tool_type=tool_attributes.get("tool_type"), **tool_params
        )
        tool_attributes["tool_params"] = tool_params
        return ToolAttributes(**tool_attributes)


ToolTypeParams = {
    ToolType.EMAIL: EmailNotificationToolParams,
    ToolType.SLACK: SlackNotificationToolParams,
    ToolType.HTTP: HTTPToolParams,
    ToolType.RAG: RAGToolParams,
    ToolType.SQL: SQLToolParams,
    ToolType.WEBSEARCH: WebSearchToolParams,
    ToolType.HUMAN: HumanToolParams,
}


class _BaseTool(ABC):

    def __init__(
        self,
        tool_name: Optional[str] = None,
        description: Optional[str] = None,
        attributes: Optional[ToolAttributes] = None,
    ):
        """Initialize an AI Agent Tool"""
        if attributes and not isinstance(attributes, ToolAttributes):
            raise TypeError(
                "'attributes' must be an object of type "
                "select_ai.agent.ToolAttributes"
            )
        self.tool_name = tool_name
        self.attributes = attributes
        self.description = description

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"tool_name={self.tool_name}, "
            f"attributes={self.attributes}, description={self.description})"
        )


class Tool(_BaseTool):

    @staticmethod
    def _get_attributes(tool_name: str) -> ToolAttributes:
        """Get attributes of an AI tool

        :return: select_ai.agent.ToolAttributes
        :raises: AgentToolNotFoundError
        """
        with cursor() as cr:
            cr.execute(
                GET_USER_AI_AGENT_TOOL_ATTRIBUTES, tool_name=tool_name.upper()
            )
            attributes = cr.fetchall()
            if attributes:
                post_processed_attributes = {}
                for k, v in attributes:
                    if isinstance(v, oracledb.LOB):
                        post_processed_attributes[k] = v.read()
                    else:
                        post_processed_attributes[k] = v
                return ToolAttributes.create(**post_processed_attributes)
            else:
                raise AgentToolNotFoundError(tool_name=tool_name)

    @staticmethod
    def _get_description(tool_name: str) -> Union[str, None]:
        with cursor() as cr:
            cr.execute(GET_USER_AI_AGENT_TOOL, tool_name=tool_name.upper())
            tool = cr.fetchone()
            if tool:
                if tool[1] is not None:
                    return tool[1].read()
                else:
                    return None
            else:
                raise AgentToolNotFoundError(tool_name=tool_name)

    def create(
        self, enabled: Optional[bool] = True, replace: Optional[bool] = False
    ):
        if self.tool_name is None:
            raise AttributeError("Tool must have a name")
        if self.attributes is None:
            raise AttributeError("Tool must have attributes")

        parameters = {
            "tool_name": self.tool_name,
            "attributes": self.attributes.json(),
        }
        if self.description:
            parameters["description"] = self.description

        if not enabled:
            parameters["status"] = "disabled"

        with cursor() as cr:
            try:
                cr.callproc(
                    "DBMS_CLOUD_AI_AGENT.CREATE_TOOL",
                    keyword_parameters=parameters,
                )
            except oracledb.Error as err:
                (err_obj,) = err.args
                if err_obj.code in (20050, 20052) and replace:
                    self.delete(force=True)
                    cr.callproc(
                        "DBMS_CLOUD_AI_AGENT.CREATE_TOOL",
                        keyword_parameters=parameters,
                    )
                else:
                    raise

    @classmethod
    def create_built_in_tool(
        cls,
        tool_name: str,
        tool_params: ToolParams,
        tool_type: ToolType,
        description: Optional[str] = None,
        replace: Optional[bool] = False,
    ) -> "Tool":
        """
        Register a built-in tool

        :param str tool_name: The name of the tool
        :param select_ai.agent.ToolParams tool_params:
         Parameters required by built-in tool
        :param select_ai.agent.ToolType tool_type: The built-in tool type
        :param str description: Description of the tool
        :param bool replace: Whether to replace the existing tool.
         Default value is False

        :return: select_ai.agent.Tool
        """
        if not isinstance(tool_params, ToolParams):
            raise TypeError(
                "'tool_params' must be an object of "
                "type select_ai.agent.ToolParams"
            )
        attributes = ToolAttributes(
            tool_params=tool_params, tool_type=tool_type
        )
        tool = cls(
            tool_name=tool_name, attributes=attributes, description=description
        )
        tool.create(replace=replace)
        return tool

    @classmethod
    def create_email_notification_tool(
        cls,
        tool_name: str,
        credential_name: str,
        recipient: str,
        sender: str,
        smtp_host: str,
        description: Optional[str],
        replace: bool = False,
    ) -> "Tool":
        """
        Register an email notification tool

        :param str tool_name: The name of the tool
        :param str credential_name: The name of the credential
        :param str recipient: The recipient of the email
        :param str sender: The sender of the email
        :param str smtp_host: The SMTP host of the email server
        :param str description: The description of the tool
        :param bool replace: Whether to replace the existing tool.
         Default value is False

        :return: select_ai.agent.Tool

        """
        email_notification_tool_params = EmailNotificationToolParams(
            credential_name=credential_name,
            recipient=recipient,
            sender=sender,
            smtp_host=smtp_host,
        )
        return cls.create_built_in_tool(
            tool_name=tool_name,
            tool_type=ToolType.EMAIL,
            tool_params=email_notification_tool_params,
            description=description,
            replace=replace,
        )

    @classmethod
    def create_http_tool(
        cls,
        tool_name: str,
        credential_name: str,
        endpoint: str,
        description: Optional[str] = None,
        replace: bool = False,
    ) -> "Tool":
        http_tool_params = HTTPToolParams(
            credential_name=credential_name, endpoint=endpoint
        )
        return cls.create_built_in_tool(
            tool_name=tool_name,
            tool_type=ToolType.HTTP,
            tool_params=http_tool_params,
            description=description,
            replace=replace,
        )

    @classmethod
    def create_pl_sql_tool(
        cls,
        tool_name: str,
        function: str,
        description: Optional[str] = None,
        replace: bool = False,
    ) -> "Tool":
        """
        Create a custom tool to invoke PL/SQL procedure or function

        :param str tool_name: The name of the tool
        :param str function: The name of the PL/SQL procedure or function
        :param str description: The description of the tool
        :param bool replace: Whether to replace existing tool. Default value
         is False

        """
        tool_attributes = ToolAttributes(function=function)
        tool = cls(
            tool_name=tool_name,
            attributes=tool_attributes,
            description=description,
        )
        tool.create(replace=replace)
        return tool

    @classmethod
    def create_rag_tool(
        cls,
        tool_name: str,
        profile_name: str,
        description: Optional[str] = None,
        replace: bool = False,
    ) -> "Tool":
        """
        Register a RAG tool, which will use a VectorIndex linked AI Profile

        :param str tool_name: The name of the tool
        :param str profile_name: The name of the profile to
         use for Vector Index based RAG
        :param str description: The description of the tool
        :param bool replace: Whether to replace existing tool. Default value
         is False
        """
        tool_params = RAGToolParams(profile_name=profile_name)
        return cls.create_built_in_tool(
            tool_name=tool_name,
            tool_type=ToolType.RAG,
            tool_params=tool_params,
            description=description,
            replace=replace,
        )

    @classmethod
    def create_sql_tool(
        cls,
        tool_name: str,
        profile_name: str,
        description: Optional[str] = None,
        replace: bool = False,
    ) -> "Tool":
        """
        Register a SQL tool to perform natural language to SQL translation

        :param str tool_name: The name of the tool
        :param str profile_name: The name of the profile to use for SQL
         translation
        :param str description: The description of the tool
        :param bool replace: Whether to replace existing tool. Default value
         is False
        """
        tool_params = SQLToolParams(profile_name=profile_name)
        return cls.create_built_in_tool(
            tool_name=tool_name,
            tool_type=ToolType.SQL,
            tool_params=tool_params,
            description=description,
            replace=replace,
        )

    @classmethod
    def create_slack_notification_tool(
        cls,
        tool_name: str,
        credential_name: str,
        slack_channel: str,
        description: Optional[str] = None,
        replace: bool = False,
    ) -> "Tool":
        """
        Register a Slack notification tool

        :param str tool_name: The name of the Slack notification tool
        :param str credential_name: The name of the Slack credential
        :param str slack_channel: The name of the Slack channel
        :param str description: The description of the Slack notification tool
        :param bool replace: Whether to replace existing tool. Default value
         is False

        """
        slack_notification_tool_params = SlackNotificationToolParams(
            credential_name=credential_name,
            slack_channel=slack_channel,
        )
        return cls.create_built_in_tool(
            tool_name=tool_name,
            tool_type=ToolType.SLACK,
            tool_params=slack_notification_tool_params,
            description=description,
            replace=replace,
        )

    @classmethod
    def create_websearch_tool(
        cls,
        tool_name: str,
        credential_name: str,
        description: Optional[str],
        replace: bool = False,
    ) -> "Tool":
        """
        Register a built-in websearch tool to search information
        on the web

        :param str tool_name: The name of the tool
        :param str credential_name: The name of the credential object
         storing OpenAI credentials
        :param str description: The description of the tool
        :param bool replace: Whether to replace the existing tool

        """
        web_search_tool_params = WebSearchToolParams(
            credential_name=credential_name,
        )
        return cls.create_built_in_tool(
            tool_name=tool_name,
            tool_type=ToolType.WEBSEARCH,
            tool_params=web_search_tool_params,
            description=description,
            replace=replace,
        )

    def delete(self, force: bool = False):
        """
        Delete AI Tool from the database

        :param bool force: Force the deletion. Default value is False.
        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI_AGENT.DROP_TOOL",
                keyword_parameters={
                    "tool_name": self.tool_name,
                    "force": force,
                },
            )

    def disable(self):
        """
        Disable AI Tool
        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI_AGENT.DISABLE_TOOL",
                keyword_parameters={
                    "tool_name": self.tool_name,
                },
            )

    def enable(self):
        """
        Enable AI Tool
        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI_AGENT.ENABLE_TOOL",
                keyword_parameters={
                    "tool_name": self.tool_name,
                },
            )

    @classmethod
    def fetch(cls, tool_name: str) -> "Tool":
        """
        Fetch AI Tool attributes from the Database and build a proxy object in
        the Python layer

        :param str tool_name: The name of the AI Task

        :return: select_ai.agent.Tool

        :raises select_ai.errors.AgentToolNotFoundError:
         If the AI Tool is not found

        """
        attributes = cls._get_attributes(tool_name)
        description = cls._get_description(tool_name)
        return cls(
            tool_name=tool_name, attributes=attributes, description=description
        )

    @classmethod
    def list(cls, tool_name_pattern: str = ".*") -> Iterator["Tool"]:
        """List AI Tools

        :param str tool_name_pattern: Regular expressions can be used
         to specify a pattern. Function REGEXP_LIKE is used to perform the
         match. Default value is ".*" i.e. match all tool name.

        :return: Iterator[Tool]
        """
        with cursor() as cr:
            cr.execute(
                LIST_USER_AI_AGENT_TOOLS,
                tool_name_pattern=tool_name_pattern,
            )
            for row in cr.fetchall():
                tool_name = row[0]
                if row[1]:
                    description = row[1].read()  # Oracle.LOB
                else:
                    description = None
                attributes = cls._get_attributes(tool_name=tool_name)
                yield cls(
                    tool_name=tool_name,
                    description=description,
                    attributes=attributes,
                )

    def set_attributes(self, attributes: ToolAttributes) -> None:
        """
        Set the attributes of the AI Agent tool
        """
        parameters = {
            "object_name": self.tool_name,
            "object_type": "tool",
            "attributes": attributes.json(),
        }
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI_AGENT.SET_ATTRIBUTES",
                keyword_parameters=parameters,
            )

    def set_attribute(self, attribute_name: str, attribute_value: Any) -> None:
        """
        Set the attribute of the AI Agent tool specified by
        `attribute_name` and `attribute_value`.
        """
        parameters = {
            "object_name": self.tool_name,
            "object_type": "tool",
            "attribute_name": attribute_name,
            "attribute_value": attribute_value,
        }
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI_AGENT.SET_ATTRIBUTE",
                keyword_parameters=parameters,
            )


class AsyncTool(_BaseTool):

    @staticmethod
    async def _get_attributes(tool_name: str) -> ToolAttributes:
        """Get attributes of an AI tool

        :return: select_ai.agent.ToolAttributes
        :raises: AgentToolNotFoundError
        """
        async with async_cursor() as cr:
            await cr.execute(
                GET_USER_AI_AGENT_TOOL_ATTRIBUTES, tool_name=tool_name.upper()
            )
            attributes = await cr.fetchall()
            if attributes:
                post_processed_attributes = {}
                for k, v in attributes:
                    if isinstance(v, oracledb.AsyncLOB):
                        post_processed_attributes[k] = await v.read()
                    else:
                        post_processed_attributes[k] = v
                return ToolAttributes.create(**post_processed_attributes)
            else:
                raise AgentToolNotFoundError(tool_name=tool_name)

    @staticmethod
    async def _get_description(tool_name: str) -> Union[str, None]:
        async with async_cursor() as cr:
            await cr.execute(
                GET_USER_AI_AGENT_TOOL, tool_name=tool_name.upper()
            )
            tool = await cr.fetchone()
            if tool:
                if tool[1] is not None:
                    return await tool[1].read()
                else:
                    return None
            else:
                raise AgentToolNotFoundError(tool_name=tool_name)

    async def create(
        self, enabled: Optional[bool] = True, replace: Optional[bool] = False
    ):
        if self.tool_name is None:
            raise AttributeError("Tool must have a name")
        if self.attributes is None:
            raise AttributeError("Tool must have attributes")

        parameters = {
            "tool_name": self.tool_name,
            "attributes": self.attributes.json(),
        }
        if self.description:
            parameters["description"] = self.description

        if not enabled:
            parameters["status"] = "disabled"

        async with async_cursor() as cr:
            try:
                await cr.callproc(
                    "DBMS_CLOUD_AI_AGENT.CREATE_TOOL",
                    keyword_parameters=parameters,
                )
            except oracledb.Error as err:
                (err_obj,) = err.args
                if err_obj.code in (20050, 20052) and replace:
                    await self.delete(force=True)
                    await cr.callproc(
                        "DBMS_CLOUD_AI_AGENT.CREATE_TOOL",
                        keyword_parameters=parameters,
                    )
                else:
                    raise

    @classmethod
    async def create_built_in_tool(
        cls,
        tool_name: str,
        tool_params: ToolParams,
        tool_type: ToolType,
        description: Optional[str] = None,
        replace: Optional[bool] = False,
    ) -> "AsyncTool":
        """
        Register a built-in tool

        :param str tool_name: The name of the tool
        :param select_ai.agent.ToolParams tool_params:
         Parameters required by built-in tool
        :param select_ai.agent.ToolType tool_type: The built-in tool type
        :param str description: Description of the tool
        :param bool replace: Whether to replace the existing tool.
         Default value is False

        :return: select_ai.agent.Tool
        """
        if not isinstance(tool_params, ToolParams):
            raise TypeError(
                "'tool_params' must be an object of "
                "type select_ai.agent.ToolParams"
            )
        attributes = ToolAttributes(
            tool_params=tool_params, tool_type=tool_type
        )
        tool = cls(
            tool_name=tool_name, attributes=attributes, description=description
        )
        await tool.create(replace=replace)
        return tool

    @classmethod
    async def create_email_notification_tool(
        cls,
        tool_name: str,
        credential_name: str,
        recipient: str,
        sender: str,
        smtp_host: str,
        description: Optional[str],
        replace: bool = False,
    ) -> "AsyncTool":
        """
        Register an email notification tool

        :param str tool_name: The name of the tool
        :param str credential_name: The name of the credential
        :param str recipient: The recipient of the email
        :param str sender: The sender of the email
        :param str smtp_host: The SMTP host of the email server
        :param str description: The description of the tool
        :param bool replace: Whether to replace the existing tool.
         Default value is False

        :return: select_ai.agent.Tool

        """
        email_notification_tool_params = EmailNotificationToolParams(
            credential_name=credential_name,
            recipient=recipient,
            sender=sender,
            smtp_host=smtp_host,
        )
        return await cls.create_built_in_tool(
            tool_name=tool_name,
            tool_type=ToolType.EMAIL,
            tool_params=email_notification_tool_params,
            description=description,
            replace=replace,
        )

    @classmethod
    async def create_http_tool(
        cls,
        tool_name: str,
        credential_name: str,
        endpoint: str,
        description: Optional[str] = None,
        replace: bool = False,
    ) -> "AsyncTool":
        http_tool_params = HTTPToolParams(
            credential_name=credential_name, endpoint=endpoint
        )
        return await cls.create_built_in_tool(
            tool_name=tool_name,
            tool_type=ToolType.HTTP,
            tool_params=http_tool_params,
            description=description,
            replace=replace,
        )

    @classmethod
    async def create_pl_sql_tool(
        cls,
        tool_name: str,
        function: str,
        description: Optional[str] = None,
        replace: bool = False,
    ) -> "AsyncTool":
        """
        Create a custom tool to invoke PL/SQL procedure or function

        :param str tool_name: The name of the tool
        :param str function: The name of the PL/SQL procedure or function
        :param str description: The description of the tool
        :param bool replace: Whether to replace existing tool. Default value
         is False

        """
        tool_attributes = ToolAttributes(function=function)
        tool = cls(
            tool_name=tool_name,
            attributes=tool_attributes,
            description=description,
        )
        await tool.create(replace=replace)
        return tool

    @classmethod
    async def create_rag_tool(
        cls,
        tool_name: str,
        profile_name: str,
        description: Optional[str] = None,
        replace: bool = False,
    ) -> "AsyncTool":
        """
        Register a RAG tool, which will use a VectorIndex linked AI Profile

        :param str tool_name: The name of the tool
        :param str profile_name: The name of the profile to
         use for Vector Index based RAG
        :param str description: The description of the tool
        :param bool replace: Whether to replace existing tool. Default value
         is False
        """
        tool_params = RAGToolParams(profile_name=profile_name)
        return await cls.create_built_in_tool(
            tool_name=tool_name,
            tool_type=ToolType.RAG,
            tool_params=tool_params,
            description=description,
            replace=replace,
        )

    @classmethod
    async def create_sql_tool(
        cls,
        tool_name: str,
        profile_name: str,
        description: Optional[str] = None,
        replace: bool = False,
    ) -> "AsyncTool":
        """
        Register a SQL tool to perform natural language to SQL translation

        :param str tool_name: The name of the tool
        :param str profile_name: The name of the profile to use for SQL
         translation
        :param str description: The description of the tool
        :param bool replace: Whether to replace existing tool. Default value
         is False
        """
        tool_params = SQLToolParams(profile_name=profile_name)
        return await cls.create_built_in_tool(
            tool_name=tool_name,
            tool_type=ToolType.SQL,
            tool_params=tool_params,
            description=description,
            replace=replace,
        )

    @classmethod
    async def create_slack_notification_tool(
        cls,
        tool_name: str,
        credential_name: str,
        slack_channel: str,
        description: Optional[str] = None,
        replace: bool = False,
    ) -> "AsyncTool":
        """
        Register a Slack notification tool

        :param str tool_name: The name of the Slack notification tool
        :param str credential_name: The name of the Slack credential
        :param str slack_channel: The name of the Slack channel
        :param str description: The description of the Slack notification tool
        :param bool replace: Whether to replace existing tool. Default value
         is False

        """
        slack_notification_tool_params = SlackNotificationToolParams(
            credential_name=credential_name,
            slack_channel=slack_channel,
        )
        return await cls.create_built_in_tool(
            tool_name=tool_name,
            tool_type=ToolType.SLACK,
            tool_params=slack_notification_tool_params,
            description=description,
            replace=replace,
        )

    @classmethod
    async def create_websearch_tool(
        cls,
        tool_name: str,
        credential_name: str,
        description: Optional[str],
        replace: bool = False,
    ) -> "AsyncTool":
        """
        Register a built-in websearch tool to search information
        on the web

        :param str tool_name: The name of the tool
        :param str credential_name: The name of the credential object
         storing OpenAI credentials
        :param str description: The description of the tool
        :param bool replace: Whether to replace the existing tool

        """
        web_search_tool_params = WebSearchToolParams(
            credential_name=credential_name,
        )
        return await cls.create_built_in_tool(
            tool_name=tool_name,
            tool_type=ToolType.WEBSEARCH,
            tool_params=web_search_tool_params,
            description=description,
            replace=replace,
        )

    async def delete(self, force: bool = False):
        """
        Delete AI Tool from the database

        :param bool force: Force the deletion. Default value is False.
        """
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI_AGENT.DROP_TOOL",
                keyword_parameters={
                    "tool_name": self.tool_name,
                    "force": force,
                },
            )

    async def disable(self):
        """
        Disable AI Tool
        """
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI_AGENT.DISABLE_TOOL",
                keyword_parameters={
                    "tool_name": self.tool_name,
                },
            )

    async def enable(self):
        """
        Enable AI Tool
        """
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI_AGENT.ENABLE_TOOL",
                keyword_parameters={
                    "tool_name": self.tool_name,
                },
            )

    @classmethod
    async def fetch(cls, tool_name: str) -> "AsyncTool":
        """
        Fetch AI Tool attributes from the Database and build a proxy object in
        the Python layer

        :param str tool_name: The name of the AI Task

        :return: select_ai.agent.Tool

        :raises select_ai.errors.AgentToolNotFoundError:
         If the AI Tool is not found

        """
        attributes = await cls._get_attributes(tool_name)
        description = await cls._get_description(tool_name)
        return cls(
            tool_name=tool_name, attributes=attributes, description=description
        )

    @classmethod
    async def list(
        cls, tool_name_pattern: str = ".*"
    ) -> AsyncGenerator["AsyncTool", None]:
        """List AI Tools

        :param str tool_name_pattern: Regular expressions can be used
         to specify a pattern. Function REGEXP_LIKE is used to perform the
         match. Default value is ".*" i.e. match all tool name.

        :return: Iterator[Tool]
        """
        async with async_cursor() as cr:
            await cr.execute(
                LIST_USER_AI_AGENT_TOOLS,
                tool_name_pattern=tool_name_pattern,
            )
            rows = await cr.fetchall()
            for row in rows:
                tool_name = row[0]
                if row[1]:
                    description = await row[1].read()  # Oracle.AsyncLOB
                else:
                    description = None
                attributes = await cls._get_attributes(tool_name=tool_name)
                yield cls(
                    tool_name=tool_name,
                    description=description,
                    attributes=attributes,
                )

    async def set_attributes(self, attributes: ToolAttributes) -> None:
        """
        Set the attributes of the AI Agent tool
        """
        parameters = {
            "object_name": self.tool_name,
            "object_type": "tool",
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
        Set the attribute of the AI Agent tool specified by
        `attribute_name` and `attribute_value`.
        """
        parameters = {
            "object_name": self.tool_name,
            "object_type": "tool",
            "attribute_name": attribute_name,
            "attribute_value": attribute_value,
        }
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI_AGENT.SET_ATTRIBUTE",
                keyword_parameters=parameters,
            )

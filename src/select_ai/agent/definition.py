# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

from typing import Optional

import oracledb

from select_ai.db import async_cursor, cursor


def get_definition(object_type: str, object_name: str) -> Optional[str]:
    """Return the canonical PL/SQL definition for an AI object.

    :param str object_type: Object type: ``AGENT``, ``TASK``, ``TOOL``, or
     ``TEAM``.
    :param str object_name: Name of the object to export.
    :return: A PL/SQL block that recreates the object, or ``None``.
    :rtype: str or None
    """
    with cursor() as cr:
        data = cr.callfunc(
            "DBMS_CLOUD_AI_AGENT.GET_DEFINITION",
            oracledb.DB_TYPE_CLOB,
            keyword_parameters={
                "object_type": object_type,
                "object_name": object_name,
            },
        )
        return data.read() if data is not None else None


async def async_get_definition(
    object_type: str, object_name: str
) -> Optional[str]:
    """Asynchronously return the canonical PL/SQL definition for an AI object.

    Parameters and return value are the same as :func:`get_definition`.
    """
    async with async_cursor() as cr:
        data = await cr.callfunc(
            "DBMS_CLOUD_AI_AGENT.GET_DEFINITION",
            oracledb.DB_TYPE_CLOB,
            keyword_parameters={
                "object_type": object_type,
                "object_name": object_name,
            },
        )
        return await data.read() if data is not None else None

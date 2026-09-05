# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

GRANT_PRIVILEGES_TO_USER = """
DECLARE
    TYPE array_t IS VARRAY(4) OF VARCHAR2(60);
    v_packages array_t;
    v_user VARCHAR2(261);
BEGIN
    v_user := DBMS_ASSERT.ENQUOTE_NAME(
        DBMS_ASSERT.SCHEMA_NAME(:user),
        FALSE
    );
    v_packages := array_t(
        'DBMS_CLOUD',
        'DBMS_CLOUD_AI',
        'DBMS_CLOUD_AI_AGENT',
        'DBMS_CLOUD_PIPELINE'
    );
    FOR i in 1..v_packages.count LOOP
        EXECUTE IMMEDIATE
            'GRANT EXECUTE ON ' || v_packages(i) || ' TO ' || v_user;
    END LOOP;
END;
"""

REVOKE_PRIVILEGES_FROM_USER = """
DECLARE
    TYPE array_t IS VARRAY(4) OF VARCHAR2(60);
    v_packages array_t;
    v_user VARCHAR2(261);
BEGIN
    v_user := DBMS_ASSERT.ENQUOTE_NAME(
        DBMS_ASSERT.SCHEMA_NAME(:user),
        FALSE
    );
    v_packages := array_t(
        'DBMS_CLOUD',
        'DBMS_CLOUD_AI',
        'DBMS_CLOUD_AI_AGENT',
        'DBMS_CLOUD_PIPELINE'
    );
    FOR i in 1..v_packages.count LOOP
        EXECUTE IMMEDIATE
            'REVOKE EXECUTE ON ' || v_packages(i) || ' FROM ' || v_user;
    END LOOP;
END;
"""

ENABLE_AI_PROFILE_DOMAIN_FOR_USER = """
BEGIN
    DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
         host => :host,
         ace  => xs$ace_type(privilege_list => xs$name_list('http'),
                             principal_name => :user,
                             principal_type => xs_acl.ptype_db)
   );
END;
"""

DISABLE_AI_PROFILE_DOMAIN_FOR_USER = """
BEGIN
    DBMS_NETWORK_ACL_ADMIN.REMOVE_HOST_ACE(
         host => :host,
         ace  => xs$ace_type(privilege_list => xs$name_list('http'),
                             principal_name => :user,
                             principal_type => xs_acl.ptype_db)
   );
END;
"""

GET_ALL_AI_PROFILE_ATTRIBUTES = """
SELECT attribute_name, attribute_value
FROM ALL_CLOUD_AI_PROFILE_ATTRIBUTES
WHERE profile_name = :profile_name
AND owner = COALESCE(:owner, SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA'))
"""

GET_ALL_AI_PROFILE = """
SELECT profile_name, description, owner
FROM ALL_CLOUD_AI_PROFILES
WHERE profile_name = :profile_name
AND owner = COALESCE(:owner, SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA'))
"""


LIST_ALL_AI_PROFILES = """
SELECT profile_name, description, owner
FROM ALL_CLOUD_AI_PROFILES
WHERE REGEXP_LIKE(profile_name, :profile_name_pattern, 'i')
AND owner = COALESCE(:owner, SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA'))
"""

LIST_ALL_VECTOR_INDEXES = """
SELECT v.index_name, v.description, v.owner
FROM ALL_CLOUD_VECTOR_INDEXES v
WHERE REGEXP_LIKE(v.index_name, :index_name_pattern, 'i')
AND v.owner = COALESCE(:owner, SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA'))
"""

GET_ALL_VECTOR_INDEX = """
SELECT index_name, description, owner
FROM ALL_CLOUD_VECTOR_INDEXES
WHERE index_name = :index_name
AND owner = COALESCE(:owner, SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA'))
"""

GET_ALL_VECTOR_INDEX_ATTRIBUTES = """
SELECT attribute_name, attribute_value
FROM ALL_CLOUD_VECTOR_INDEX_ATTRIBUTES
WHERE index_name = :index_name
AND owner = COALESCE(:owner, SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA'))
"""

LIST_USER_CONVERSATIONS = """
SELECT conversation_id,
       conversation_title,
       description,
       retention_days
from USER_CLOUD_AI_CONVERSATIONS
"""

GET_USER_CONVERSATION_ATTRIBUTES = """
SELECT conversation_title,
       description,
       retention_days
from USER_CLOUD_AI_CONVERSATIONS
WHERE conversation_id = :conversation_id
"""


LIST_USER_CONVERSATION_PROMPTS = """
SELECT conversation_prompt_id,
       conversation_id,
       conversation_title,
       profile_name,
       prompt_action,
       prompt,
       prompt_response,
       created,
       modified,
       client_identifier,
       client_ip,
       sid,
       serial#
FROM USER_CLOUD_AI_CONVERSATION_PROMPTS
WHERE conversation_id = :conversation_id
ORDER BY created
"""


GET_VECTOR_PIPELINE_LAST_EXECUTION = """
SELECT CAST(last_execution AT TIME ZONE 'UTC' AS TIMESTAMP)
FROM USER_CLOUD_PIPELINES
WHERE pipeline_name = :pipeline_name
"""

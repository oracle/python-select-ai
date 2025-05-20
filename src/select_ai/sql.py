GRANT_PRIVILEGES_TO_USER = """
DECLARE
    TYPE array_t IS VARRAY(3) OF VARCHAR2(60);
    v_packages array_t;
BEGIN
    v_packages := array_t(
        'DBMS_CLOUD', 'DBMS_CLOUD_AI', 'DBMS_CLOUD_PIPELINE'
    );
    FOR i in 1..v_packages.count LOOP
        EXECUTE IMMEDIATE
            'GRANT EXECUTE ON ' || v_packages(i) || ' TO {0}';
    END LOOP;
END;
"""

REVOKE_PRIVILEGES_FROM_USER = """
DECLARE
    TYPE array_t IS VARRAY(3) OF VARCHAR2(60);
    v_packages array_t;
BEGIN
    v_packages := array_t(
        'DBMS_CLOUD', 'DBMS_CLOUD_AI', 'DBMS_CLOUD_PIPELINE'
    );
    FOR i in 1..v_packages.count LOOP
        EXECUTE IMMEDIATE
            'REVOKE EXECUTE ON ' || v_packages(i) || ' FROM {0}';
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

GET_USER_AI_PROFILE_ATTRIBUTES = """
SELECT attribute_name, attribute_value
FROM USER_CLOUD_AI_PROFILE_ATTRIBUTES
WHERE profile_name = :profile_name
"""

GET_USER_AI_PROFILE = """
SELECT count(*)
FROM  USER_CLOUD_AI_PROFILES
WHERE profile_name = :profile_name
"""


GET_USER_VECTOR_INDEX_ATTRIBUTES = """
SELECT attribute_name, attribute_value
FROM USER_CLOUD_VECTOR_INDEX_ATTRIBUTES
WHERE INDEX_NAME = :index_name
"""

LIST_USER_AI_PROFILES = """
SELECT profile_name, description
FROM USER_CLOUD_AI_PROFILES
WHERE REGEXP_LIKE(profile_name, :profile_name_pattern, 'i')
"""

LIST_USER_VECTOR_INDEXES_BY_PROFILE = """
SELECT v.index_name, v.description
FROM USER_CLOUD_VECTOR_INDEXES v,
USER_CLOUD_VECTOR_INDEX_ATTRIBUTES a
WHERE lower(a.attribute_name) = 'profile_name'
AND DBMS_LOB.compare(a.attribute_value, TO_CLOB(:profile_name)) = 0
AND REGEXP_LIKE(v.index_name, :index_name_pattern, 'i')
AND v.index_name = a.index_name
"""

LIST_CONVERSATIONS = """

"""

.. _agent:

``select_ai.agent`` adds a thin Python layer over Oracle Autonomous Database's
``DBMS_CLOUD_AI_AGENT`` package so you can define tools, compose tasks, wire up
agents and run teams from Python using the existing select_ai connection objects

- Keep agent state and orchestration in the database

- Register callable tools (PL/SQL procedure or functions, SQL, external HTTP
  endpoints, Slack or Email notifications) and attach them to tasks

- Group agents into teams and invoke them with a single API call

.. latex:clearpage::

********
``Tool``
********

A callable which Select AI agent can invoke to accomplish a certain task.
Users can either register built-in tools or create a custom tool using a PL/SQL
stored procedure.

Supported Tools
+++++++++++++++

Following class methods of ``select_ai.agent.Tool`` class
can be used to create tools. Invoking them will create a proxy object in the
Python layer and persist the tool in the Database using
``DBMS_CLOUD_AI_AGENT.CREATE_TOOL``


.. list-table:: Select AI Agent Tools
    :header-rows: 1
    :widths: 20 50 30
    :align: left

    * - Tool Type
      - Class Method
      - Arguments
    * - ``EMAIL``
      - ``select_ai.agent.Tool.create_email_notification_tool``
      -  - ``tool_name``
         - ``credential_name``
         - ``recipient``
         - ``sender``
         - ``smtp_host``
    * - ``HTTP``
      - ``select_ai.agent.Tool.create_http_tool``
      - - ``tool_name``
        - ``credential_name``
        - ``endpoint``
    * - ``SQL``
      - ``select_ai.agent.Tool.create_sql_tool``
      - - ``tool_name``
        - ``profile_name``
    * - ``SLACK``
      - ``select_ai.agent.Tool.create_slack_notification_tool``
      - - ``tool_name``
        - ``credential_name``
        - ``slack_channel``
    * - ``WEBSEARCH``
      - ``select_ai.agent.Tool.create_websearch_tool``
      - - ``tool_name``
        - ``credential_name``
    * - ``PL/SQL custom tool``
      - ``select_ai.agent.Tool.create_pl_sql_tool``
      - - ``tool_name``
        - ``function``
    * - ``RAG``
      - ``select_ai.agent.Tool.create_rag_tool``
      - - ``tool_name``
        - ``profile_name``

.. latex:clearpage::

.. autoclass:: select_ai.agent.ToolAttributes
   :members:

.. autoclass:: select_ai.agent.ToolParams
   :members:

.. latex:clearpage::

.. autoclass:: select_ai.agent.Tool
   :members:

.. latex:clearpage::

Create Tool
+++++++++++

The following example shows creation of an AI agent tool to perform natural
language translation to SQL using an OCI AI profile

.. literalinclude:: ../../../samples/agent/tool_create.py
   :language: python
   :lines: 14-

.. latex:clearpage::

output::

    MOVIE_SQL_TOOL

    ToolAttributes(instruction=None,
                   function=None,
                   tool_params=SQLToolParams(_REQUIRED_FIELDS=None,
                                             credential_name=None,
                                             endpoint=None,
                                             notification_type=None,
                                             profile_name='oci_ai_profile',
                                             recipient=None,
                                             sender=None,
                                             slack_channel=None,
                                             smtp_host=None),
                   tool_inputs=None,
                   tool_type=<ToolType.SQL: 'SQL'>)



.. latex:clearpage::


List Tools
++++++++++

.. literalinclude:: ../../../samples/agent/tool_list.py
   :language: python
   :lines: 14-

output::

    Tool(tool_name=MOVIE_SQL_TOOL, attributes=ToolAttributes(instruction='This tool is used to work with SQL queries using natural language. Input should be a natural language query about data or database operations. The tool behavior depends on the configured action: RUNSQL - generates and executes the SQL query returning actual data; SHOWSQL - generates and displays the SQL statement without executing it; EXPLAINSQL - generates SQL and provides a natural language explanation of what the query does. Always provide clear, specific questions about the data you want to retrieve or analyze.', function='dbms_cloud_ai_agent.sql_tool', tool_params=SQLToolParams(_REQUIRED_FIELDS=None, credential_name=None, endpoint=None, notification_type=None, profile_name='oci_ai_profile', recipient=None, sender=None, slack_channel=None, smtp_host=None), tool_inputs=None, tool_type='SQL'), description=My Select AI MOVIE SQL agent tool)

    Tool(tool_name=LLM_CHAT_TOOL, attributes=ToolAttributes(instruction='This tool is used to work with SQL queries using natural language. Input should be a natural language query about data or database operations. The tool behavior depends on the configured action: RUNSQL - generates and executes the SQL query returning actual data; SHOWSQL - generates and displays the SQL statement without executing it; EXPLAINSQL - generates SQL and provides a natural language explanation of what the query does. Always provide clear, specific questions about the data you want to retrieve or analyze.', function='dbms_cloud_ai_agent.sql_tool', tool_params=SQLToolParams(_REQUIRED_FIELDS=None, credential_name=None, endpoint=None, notification_type=None, profile_name='oci_ai_profile', recipient=None, sender=None, slack_channel=None, smtp_host=None), tool_inputs=None, tool_type='SQL'), description=My Select AI agent tool)

.. latex:clearpage::

********
``Task``
********

Each task is identified by a ``task_name`` and includes a set of attributes that
guide the agent’s behavior during execution.
Key attributes include the ``instruction``, which describes the task’s purpose and
provides context for the agent to reason about when and how to use it,
and the ``tools`` list, which specifies which tools the agent can choose from to
accomplish the task. An optional ``input`` field allows a task to depend on the
output of prior tasks, enabling task chaining and multi-step workflows.

.. autoclass:: select_ai.agent.TaskAttributes
   :members:

.. latex:clearpage::

.. autoclass:: select_ai.agent.Task
   :members:

.. latex:clearpage::


Create Task
+++++++++++

In the following task, we use the ``MOVIE_SQL_TOOL`` created in the
previous step

.. literalinclude:: ../../../samples/agent/task_create.py
   :language: python

output::

    ANALYZE_MOVIE_TASK

    TaskAttributes(instruction='Help the user with their request about movies. '
                               'User question: {query}. You can use SQL tool to '
                               'search the data from database',
                   tools=['MOVIE_SQL_TOOL'],
                   input=None,
                   enable_human_tool=False)


.. latex:clearpage::

List Tasks
+++++++++++

.. literalinclude:: ../../../samples/agent/tasks_list.py
   :language: python

output::

    Task(task_name=ANALYZE_MOVIE_TASK, attributes=TaskAttributes(instruction='Help the user with their request about movies. User question: {query}. You can use SQL tool to search the data from database', tools='["MOVIE_SQL_TOOL"]', input=None, enable_human_tool=False), description=Movie task involving a human)

.. latex:clearpage::

*********
``Agent``
*********

A Select AI Agent is defined using ``agent_name``, its ``attributes`` and an
optional description. The attributes must include key agent properties such as
``profile_name`` which specifies the LLM profile used for prompt generation
and ``role``, which outlines the agent’s intended role and behavioral context.

.. autoclass:: select_ai.agent.AgentAttributes
   :members:

.. latex:clearpage::

.. autoclass:: select_ai.agent.Agent
   :members:

.. latex:clearpage::

Create Agent
++++++++++++

.. literalinclude:: ../../../samples/agent/agent_create.py
   :language: python

output::

    Created Agent: Agent(agent_name=MOVIE_ANALYST, attributes=AgentAttributes(profile_name='LLAMA_4_MAVERICK', role='You are an AI Movie Analyst. Your can help answer a variety of questions related to movies. ', enable_human_tool=False), description=None)


.. latex:clearpage::

****
Team
****

AI Agent Team coordinates the execution of multiple agents working together to
fulfill a user request. Each team is uniquely identified by a ``team_name`` and
configured through a set of ``attributes`` that define its composition and
execution strategy. The ``agents`` attribute specifies an array of agent-task
pairings, allowing users to assign specific tasks to designated agents. User
can perform multiple tasks by assigning the same agent to different tasks.
The ``process`` attribute defines how tasks should be executed.

.. autoclass:: select_ai.agent.TeamAttributes
   :members:

.. latex:clearpage::

.. autoclass:: select_ai.agent.Team
   :members:

.. latex:clearpage::

Run Team
++++++++

.. literalinclude:: ../../../samples/agent/team_create.py
   :language: python

output::

    To list the movies, you can use the SQL query: SELECT m.* FROM "SPARK_DB_USER"."MOVIE" m.

.. latex:clearpage::

*****************
AI agent examples
*****************

Web Search Agent using OpenAI's GPT model
+++++++++++++++++++++++++++++++++++++++++

.. literalinclude:: ../../../samples/agent/websearch_agent.py
   :language: python

output::

    Created credential:  OPENAI_CRED
    Created profile:  OPENAI_PROFILE
    Created tool:  WEB_SEARCH_TOOL
    The key features of Oracle Database Machine Learning, as highlighted on the Oracle website, include:

    - In-database machine learning: Build, train, and deploy machine learning models directly inside the Oracle Database, eliminating the need to move data.
    - Support for multiple languages: Use SQL, Python, and R for machine learning tasks, allowing flexibility for data scientists and developers.
    - Automated machine learning (AutoML): Automates feature selection, model selection, and hyperparameter tuning to speed up model development.
    - Scalability and performance: Utilizes Oracle Database’s scalability, security, and high performance for machine learning workloads.
    - Integration with Oracle Cloud: Seamlessly integrates with Oracle Cloud Infrastructure for scalable and secure deployment.
    - Security and governance: Inherits Oracle Database’s robust security, data privacy, and governance features.
    - Prebuilt algorithms: Offers a wide range of in-database algorithms for classification, regression, clustering, anomaly detection, and more.
    - No data movement: Keeps data secure and compliant by performing analytics and machine learning where the data resides.

    These features enable organizations to operationalize machine learning at scale, improve productivity, and maintain data security and compliance.

    The main topic at the URL https://www.oracle.com/artificial-intelligence/database-machine-learning is Oracle's database machine learning capabilities, specifically how Oracle integrates artificial intelligence and machine learning features directly into its database products. The page highlights how users can leverage these built-in AI and ML tools to analyze data, build predictive models, and enhance business applications without moving data outside the Oracle Database environment.

    The main topic of the website https://openai.com is artificial intelligence research and development. OpenAI focuses on creating and promoting advanced AI technologies, including products like ChatGPT, and provides information about their research, products, and mission to ensure that artificial general intelligence benefits all of humanity.

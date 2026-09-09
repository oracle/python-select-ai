.. _async_agent:

``select_ai.agent`` also provides async interfaces to be used with
``async`` / ``await`` keywords. Use these classes in applications that already
use ``asyncio`` and ``select_ai.async_connect()`` or
``select_ai.create_pool_async()``.

The history API follows the same pattern. ``AsyncTeamHistory``,
``AsyncTaskHistory``, and ``AsyncToolHistory`` query only the current user's
history views and yield typed events newest first.
See :ref:`async-agent-history` for the complete API reference and sample.

.. code-block:: python

   from select_ai.agent import AsyncToolHistory

   async for call in AsyncToolHistory.list(limit=10):
       print(call.tool_name, call.output)

The async sample retrieves a team's latest execution and uses its
``team_exec_id`` to retrieve the associated task and tool history.

The async agent object model mirrors the synchronous agent object model:

.. list-table:: Sync and async agent APIs
   :header-rows: 1
   :widths: 50 50
   :align: left

   * - Sync class
     - Async class
   * - ``select_ai.agent.Tool``
     - ``select_ai.agent.AsyncTool``
   * - ``select_ai.agent.Task``
     - ``select_ai.agent.AsyncTask``
   * - ``select_ai.agent.Agent``
     - ``select_ai.agent.AsyncAgent``
   * - ``select_ai.agent.Team``
     - ``select_ai.agent.AsyncTeam``

Create or reuse the same database objects as the synchronous APIs. Async
methods must be awaited, and async list methods return async iterators.

.. code-block:: python

   await select_ai.async_connect(user=user, password=password, dsn=dsn)

   async for tool in select_ai.agent.AsyncTool.list():
       print(tool.tool_name)

Tools, tasks, agents, and teams are database objects. Use ``replace=True`` when
you want to recreate an existing object with the same name, and ``force=True``
when cleanup should succeed even if the object does not exist.

.. list-table:: Select AI Async Agent Tools
    :header-rows: 1
    :widths: 20 50 30
    :align: left

    * - Tool Type
      - AsyncTool Class Method
      - Arguments
    * - ``EMAIL``
      - ``select_ai.agent.AsyncTool.create_email_notification_tool``
      -  - ``tool_name``
         - ``credential_name``
         - ``recipient``
         - ``sender``
         - ``smtp_host``
    * - ``SQL``
      - ``select_ai.agent.AsyncTool.create_sql_tool``
      - - ``tool_name``
        - ``profile_name``
    * - ``SLACK``
      - ``select_ai.agent.AsyncTool.create_slack_notification_tool``
      - - ``tool_name``
        - ``credential_name``
        - ``channel``
    * - ``WEBSEARCH``
      - ``select_ai.agent.AsyncTool.create_websearch_tool``
      - - ``tool_name``
        - ``credential_name``
    * - ``PL/SQL custom tool``
      - ``select_ai.agent.AsyncTool.create_pl_sql_tool``
      - - ``tool_name``
        - ``function``
    * - ``RAG``
      - ``select_ai.agent.AsyncTool.create_rag_tool``
      - - ``tool_name``
        - ``profile_name``

Notification and web search tools require credentials and network access for
the external service. SQL and RAG tools require existing Select AI profiles.

Tool selection follows the same guidance as :ref:`Agent <agent>`: use SQL
tools for database questions, RAG tools for vector-index-backed content,
notification tools for Slack or email, web search tools for public web content,
and PL/SQL tools for application-specific database logic.

*************
``AsyncTool``
*************

.. autoclass:: select_ai.agent.AsyncTool
   :members:

.. latex:clearpage::

Create Tool
+++++++++++

The following example shows async creation of an AI agent tool to perform
natural language translation to SQL using an OCI AI profile

.. literalinclude:: ../../../samples/agent/async/tool_create.py
   :language: python
   :lines: 14-

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
                                             channel=None,
                                             smtp_host=None),
                   tool_inputs=None,
                   tool_type=<ToolType.SQL: 'SQL'>)

.. latex:clearpage::

List Tools
++++++++++

.. literalinclude:: ../../../samples/agent/async/tools_list.py
   :language: python
   :lines: 14-

output::

    WEB_SEARCH_TOOL
    MOVIE_SQL_TOOL
    LLM_CHAT_TOOL

.. latex:clearpage::

Inspect and run a tool
++++++++++++++++++++++

Use ``AsyncTool.describe_tool()`` to return JSON metadata for a tool, including
its function arguments. Use ``AsyncTool.run_tool(input)`` to invoke a tool
directly with an input payload.

.. code-block:: python

   tool = await AsyncTool.fetch("MOVIE_SQL_TOOL")
   print(await tool.describe_tool())
   print(await tool.run_tool('{"query": "How many movies are there?"}'))

The complete example creates a temporary PL/SQL tool, describes it, invokes it,
and removes the temporary database objects:

.. literalinclude:: ../../../samples/agent/async/tool_run_describe.py
   :language: python
   :lines: 14-

The generated tool name and calculated age vary between runs. Representative
output is:

output::

    Tool description:
    {"tool_name": "SAMPLE_AGE_TOOL_<generated suffix>", ...}
    Tool result:
    <calculated age in years>

.. latex:clearpage::


*************
``AsyncTask``
*************

.. autoclass:: select_ai.agent.AsyncTask
   :members:

.. latex:clearpage::

Create Task
+++++++++++

In the following task, we use the ``MOVIE_SQL_TOOL`` created in the
previous step

The ``instruction`` is the main task prompt. Use placeholders such as
``{query}`` when the user prompt should be inserted into the task. The
``tools`` list limits which tools the agent can use for the task.

.. literalinclude:: ../../../samples/agent/async/task_create.py
   :language: python
   :lines: 13-

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

.. literalinclude:: ../../../samples/agent/async/tasks_list.py
   :language: python
   :lines: 13-

output::

    WEB_SEARCH_TASK
    ANALYZE_MOVIE_TASK

.. latex:clearpage::

**************
``AsyncAgent``
**************

.. autoclass:: select_ai.agent.AsyncAgent
   :members:

.. latex:clearpage::

Create Agent
++++++++++++

.. literalinclude:: ../../../samples/agent/async/agent_create.py
   :language: python
   :lines: 14-

output::

    Created Agent: Agent(agent_name=MOVIE_ANALYST,
    attributes=AgentAttributes(profile_name='LLAMA_4_MAVERICK',
    role='You are an AI Movie Analyst.
    Your can help answer a variety of questions related to movies. ',
    enable_human_tool=False), description=None)

List Agents
++++++++++++

.. literalinclude:: ../../../samples/agent/async/agents_list.py
   :language: python
   :lines: 14-

output::

    WEB_SEARCH_AGENT
    MOVIE_ANALYST


.. latex:clearpage::

**********
AsyncTeam
**********


.. autoclass:: select_ai.agent.AsyncTeam
   :members:

Share an async team
+++++++++++++++++++

Grant or revoke access for a database user or role with ``AsyncTeam`` methods.
Run these methods as the team owner:

.. code-block:: python

   team = await AsyncTeam.fetch("MOVIE_AGENT_TEAM")
   await team.grant_access("APP_USER")
   await team.revoke_access("APP_USER")

Team fetch and list operations use the connected user's agent-team views and do
not currently accept an ``owner`` argument.

Supervised teams
++++++++++++++++

Configure an asynchronous supervised team in the same way as a synchronous
team. Set ``supervisor=True`` on the coordinating agent and pass its name as
``TeamAttributes.supervisor_agent``. Keep the worker agent and task
assignments in the team's ``agents`` list.

The database creates the supervisor task when the team is created, so
``supervisor_task`` should not be supplied by the application. Fetch the team
after creation to read the generated value from
``fetched.attributes.supervisor_task``.

.. code-block:: python

   supervisor = AsyncAgent(
       agent_name="MOVIE_SUPERVISOR",
       attributes=AgentAttributes(
           profile_name="oci_ai_profile",
           role="You supervise and coordinate the team.",
           supervisor=True,
       ),
   )

   team = AsyncTeam(
       team_name="MOVIE_AGENT_TEAM",
       attributes=TeamAttributes(
           agents=[
               {"name": "MOVIE_ANALYST", "task": "ANALYZE_MOVIE_TASK"}
           ],
           process="sequential",
           supervisor_agent=supervisor.agent_name,
       ),
   )

The complete asynchronous example creates the team, runs a prompt through the
supervisor workflow, and inspects its generated supervisor task and metadata.
``AsyncTeam.run()`` starts the team workflow; the configured supervisor agent
coordinates the worker agent as part of that call.

.. literalinclude:: ../../../samples/agent/async/team_supervisor_inspect.py
   :language: python
   :lines: 14-

The generated names and returned JSON metadata vary between runs. Representative
output is:

output::

    Team response: <answer from the supervised team>
    Supervisor agent: SAMPLE_SUPERVISOR_<generated suffix>
    Supervisor task: <generated supervisor task>
    Team description: <JSON team metadata>
    Team tools: <JSON tool metadata>

.. latex:clearpage::

Run Team
++++++++

``AsyncTeam.run(...)`` starts the team workflow. The ``prompt`` argument is
passed to the task and can be referenced by task instructions using
``{query}``. ``params`` can include ``conversation_id`` to associate multiple
runs with the same conversation and ``variables`` to pass additional key-value
inputs.

.. code-block:: python

   result = await team.run(
       prompt="Could you list the movies in the database?",
       params={
           "conversation_id": conversation_id,
           "variables": {"audience": "analyst"},
       },
   )

.. literalinclude:: ../../../samples/agent/async/team_create.py
   :language: python
   :lines: 14-

output::

    The database contains 100 movies with various titles, genres, and release
    dates. The list includes a wide range of genres such as Action, Comedy, Drama,
    Thriller, Romance, Adventure, Mystery, Sci-Fi, Historical, Biography, War,
    Sports, Music, Documentary, Animated, Fantasy, Horror, Western, Family,
    and more. The release dates are primarily in January and February of 2019.
    Here is a summary of the movies:

    1. Action Movie (Action, 2019-01-01)
    2. Comedy Film (Comedy, 2019-01-02)
    3. Drama Series (Drama, 2019-01-03)
    4. Thriller Night (Thriller, 2019-01-04)
    5. Romance Story (Romance, 2019-01-05)
    6. Adventure Time (Adventure, 2019-01-06)
    7. Mystery Solver (Mystery, 2019-01-07)
    8. Sci-Fi World (Sci-Fi, 2019-01-08)
    9. Historical Epic (Historical, 2019-01-09)
    10. Biographical (Biography, 2019-01-10)
    ... (list continues up to 100 movies)

.. latex:clearpage::


Export and Import Team
++++++++++++++++++++++

Select AI agent teams can be exported into a portable specification and
imported into the same database, a different database, or another Select AI
service. The specification describes the team composition and the associated
agent, task, and tool definitions that are needed to recreate the team.

``AsyncTeam.export_team()`` returns the specification as a JSON string by
default. ``AsyncTeam.import_team()`` accepts either that JSON string or a Python
mapping containing the same team definition structure. In most cases, pass a
``dict``, for example the result of ``json.loads(exported_spec)``. Other
JSON-serializable `collections.abc.Mapping <https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping>`__
objects, such as ``OrderedDict``, can also be used. On import,
``profile_name`` identifies the Select AI profile to use in the target
database. ``team_name`` can be provided to create the imported team under a new
name; this is useful when importing into the same database as the source team.

If imported object names conflict with existing agents, tasks, tools, or teams,
set ``force=True`` to let the database replace the conflicting objects. Use this
carefully when importing into a shared schema because conflicting components can
be dropped and recreated.

.. literalinclude:: ../../../samples/agent/async/team_export_import.py
   :language: python
   :lines: 14-

output::

    Exported specification:
    {
      "name": "EXPORT_IMPORT_MOVIE_ANALYST",
      "component_type": "Agent",
      "task": {
        "task_name": "EXPORT_IMPORT_MOVIE_TASK",
        "instruction": "Help the user with movie questions. Question: {query}",
        "task_attributes": {
          "enable_human_tool": "false",
          "tools": []
        }
      },
      "llm_config": {
        "name": "LLAMA_4_MAVERICK",
        "component_type": "oci"
      }
    }
    Imported team: AsyncTeam(team_name=IMPORTED_MOVIE_AGENT_TEAM, ...)

The same APIs can also read from or write to object storage by passing both
``object_storage_credential_name`` and ``location``. When exporting to object
storage, ``AsyncTeam.export_team()`` writes the specification to the location
and returns ``None``. When importing from object storage, pass the same
credential and location instead of ``specification``.

Inspect a team
++++++++++++++

``AsyncTeam.describe_team()`` returns JSON metadata and the aggregated skills
for a team. ``AsyncTeam.list_tools()`` returns JSON metadata for the tools
available to that team.

.. code-block:: python

   team = await AsyncTeam.fetch("MOVIE_AGENT_TEAM")
   print(await team.describe_team())
   print(await team.list_tools())

The asynchronous supervised-team sample also demonstrates both inspection
methods.

.. latex:clearpage::

Lifecycle helpers
+++++++++++++++++

All async agent object types support list, fetch, enable, disable, and delete
operations.

.. code-block:: python

   async for tool in select_ai.agent.AsyncTool.list():
       print(tool.tool_name)

   task = await select_ai.agent.AsyncTask.fetch("ANALYZE_MOVIE_TASK")
   agent = await select_ai.agent.AsyncAgent.fetch("MOVIE_ANALYST")
   team = await select_ai.agent.AsyncTeam.fetch("MOVIE_AGENT_TEAM")

   await team.disable()
   await team.enable()
   await team.delete(force=True)

.. latex:clearpage::

Object definitions
******************

Use ``async_get_definition(object_type, object_name)`` to asynchronously
retrieve the canonical PL/SQL block for recreating an AI ``AGENT``, ``TASK``,
``TOOL``, or ``TEAM``. The function returns ``None`` when the database does not
return a definition.

.. code-block:: python

   from select_ai.agent import async_get_definition

   definition = await async_get_definition("TASK", "ANALYZE_MOVIE_TASK")
   print(definition)

See the asynchronous definition sample for a complete create, inspect, and
cleanup flow.

.. literalinclude:: ../../../samples/agent/async/get_definition.py
   :language: python
   :lines: 14-

The task name and exact PL/SQL formatting vary between runs and database
versions. Representative output is:

output::

    BEGIN
      DBMS_CLOUD_AI_AGENT.CREATE_TASK(...);
    END;
    /

.. latex:clearpage::


.. _async-agent-history:

********************
Async agent history
********************

``AsyncTeamHistory``, ``AsyncTaskHistory``, and
``AsyncToolHistory`` provide asynchronous, read-only access to the current
user's Select AI Agent history views. Their ``list()`` methods return async
iterators ordered from newest to oldest.

Use ``team_exec_id`` from a team event to scope task and tool history to the
same execution. Filters such as ``team_name``, ``task_name``,
``agent_name``, and ``tool_name`` can be used when an execution
identifier is not available. Tool ``input`` and ``output`` values
are decoded to Python objects when they contain valid JSON.

.. code-block:: python

   from select_ai.agent import (
       AsyncTaskHistory,
       AsyncTeamHistory,
       AsyncToolHistory,
   )

   async for team_run in AsyncTeamHistory.list(
       team_name="ORACLE_AI_DATABASE_AGENT",
       limit=1,
   ):
       print(team_run)
       async for task_run in AsyncTaskHistory.list(
           team_exec_id=team_run.team_exec_id
       ):
           print(task_run)
       async for tool_run in AsyncToolHistory.list(
           team_exec_id=team_run.team_exec_id
       ):
           print(tool_run)

The complete sample retrieves a team's latest execution and uses its
``team_exec_id`` to retrieve the associated task and tool history:

.. autoclass:: select_ai.agent.AsyncTeamHistory
   :members:

.. autoclass:: select_ai.agent.AsyncTaskHistory
   :members:

.. autoclass:: select_ai.agent.AsyncToolHistory
   :members:

.. literalinclude:: ../../../samples/agent/async/agent_history_list.py
   :language: python
   :lines: 14-

History depends on an existing execution for the configured team. Representative
output is:

output::

    TeamHistoryEvent(team_exec_id='<team execution id>', team_name='ORACLE_AI_DATABASE_AGENT', state='<state>', ...)
    TaskHistoryEvent(team_exec_id='<team execution id>', task_name='<task name>', state='<state>', ...)
    ToolHistoryEvent(invocation_id=<invocation id>, team_exec_id='<team execution id>', tool_name='<tool name>', ...)

.. latex:clearpage::

List Teams
++++++++++

.. literalinclude:: ../../../samples/agent/async/teams_list.py
   :language: python
   :lines: 13-

output::

    WEB_SEARCH_TEAM
    MOVIE_AGENT_TEAM


.. latex:clearpage::

***********************
Async AI agent examples
***********************

Web Search Agent using OpenAI's GPT model
+++++++++++++++++++++++++++++++++++++++++

.. literalinclude:: ../../../samples/agent/async/websearch_agent.py
   :language: python
   :lines: 14-

output::

    Created credential:  OPENAI_CRED
    Created profile:  OPENAI_PROFILE
    Created tool:  WEB_SEARCH_TOOL
    The key features of Oracle Database Machine Learning, as highlighted on the
     Oracle website, include:

    - In-database machine learning: Build, train, and deploy machine learning
      models directly inside the Oracle Database, eliminating the need to move
      data.
    - Support for multiple languages: Use SQL, Python, and R for machine
      learning tasks, allowing flexibility for data scientists and developers.
    - Automated machine learning (AutoML): Automates feature selection, model
      selection, and hyperparameter tuning to speed up model development.
    - Scalability and performance: Utilizes Oracle Database’s scalability,
      security, and high performance for machine learning workloads.
    - Integration with Oracle Cloud: Seamlessly integrates with Oracle
      Cloud Infrastructure for scalable and secure deployment.
    - Security and governance: Inherits Oracle Database’s robust security,
      data privacy, and governance features.
    - Prebuilt algorithms: Offers a wide range of in-database algorithms for
      classification, regression, clustering, anomaly detection, and more.
    - No data movement: Keeps data secure and compliant by performing
      analytics and machine learning where the data resides.

    These features enable organizations to operationalize machine learning at
    scale, improve productivity, and maintain data security and compliance.

    The main topic at the URL https://www.oracle.com/artificial-intelligence/database-machine-learning
    is Oracle's database machine learning capabilities, specifically how Oracle
    integrates artificial intelligence and machine learning features directly
    into its database products. The page highlights how users can leverage these
    built-in AI and ML tools to analyze data, build predictive models, and enhance
    business applications without moving data outside the Oracle Database
    environment.

    The main topic of the website https://openai.com is artificial
    intelligence research and development. OpenAI focuses on creating and
     promoting advanced AI technologies, including products like ChatGPT, and
     provides information about their research, products, and mission to ensure
     that artificial general intelligence benefits all of humanity.

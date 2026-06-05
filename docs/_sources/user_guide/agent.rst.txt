.. _agent:

``select_ai.agent`` adds a thin Python layer over Oracle Autonomous Database's
``DBMS_CLOUD_AI_AGENT`` package so you can define tools, compose tasks, wire up
agents and run teams from Python using the existing Select AI connection
objects.

- Keep agent state and orchestration in the database

- Register callable tools (PL/SQL procedure or functions, SQL, external HTTP
  endpoints, Slack or Email notifications) and attach them to tasks

- Group agents into teams and invoke them with a single API call

Agent workflows build on the same setup used by profiles: connect to Oracle
Database, create or reuse a Select AI profile, create credentials for any
external service used by tools, and grant network access for external
endpoints. See :ref:`Connection <conn>`, :ref:`Profile <profile>`,
:ref:`Credential <credential>`, and :ref:`Privileges <privileges>`.

The usual agent workflow is:

* Create tools that an agent can use.
* Create tasks that describe the work and list the tools available for that
  task.
* Create an agent with a role and an LLM profile.
* Create a team that pairs agents with tasks.
* Run the team with a user prompt.

Tools, tasks, agents, and teams are database objects. Use ``replace=True`` when
you want to recreate an existing object with the same name, and ``force=True``
when cleanup should succeed even if the object does not exist.

.. latex:clearpage::

********
``Tool``
********

A callable which Select AI agent can invoke to accomplish a certain task.
Users can either register built-in tools or create a custom tool using a PL/SQL
stored procedure.

Use focused tools with clear instructions. The task and agent prompts decide
when tools are used, so tool names, descriptions, and instructions should be
specific enough for the model to choose the right tool.

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
    * - ``SQL``
      - ``select_ai.agent.Tool.create_sql_tool``
      - - ``tool_name``
        - ``profile_name``
    * - ``SLACK``
      - ``select_ai.agent.Tool.create_slack_notification_tool``
      - - ``tool_name``
        - ``credential_name``
        - ``channel``
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

Tool selection
++++++++++++++

.. list-table:: When to use each tool
    :header-rows: 1
    :widths: 25 75
    :align: left

    * - Tool type
      - Use case
    * - ``SQL``
      - Ask questions over database objects using a Select AI profile.
    * - ``RAG``
      - Answer questions using content indexed by a vector index profile.
    * - ``WEBSEARCH``
      - Search public web content using a web search credential.
    * - ``SLACK``
      - Send a Slack notification from an agent workflow.
    * - ``EMAIL``
      - Send an email notification from an agent workflow.
    * - ``PL/SQL custom tool``
      - Call a database procedure or function for application-specific work.

Notification and web search tools require credentials and network access for
the external service. SQL and RAG tools require existing Select AI profiles.

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
                                             channel=None,
                                             smtp_host=None),
                   tool_inputs=None,
                   tool_type=<ToolType.SQL: 'SQL'>)



.. latex:clearpage::


List Tools
++++++++++

.. literalinclude:: ../../../samples/agent/tools_list.py
   :language: python
   :lines: 14-

output::

    WEB_SEARCH_TOOL
    MOVIE_SQL_TOOL
    LLM_CHAT_TOOL

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

The ``instruction`` is the main task prompt. Use placeholders such as
``{query}`` when the user prompt should be inserted into the task. The
``tools`` list limits which tools the agent can use for the task.

.. literalinclude:: ../../../samples/agent/task_create.py
   :language: python
   :lines: 14-

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
   :lines: 14-

output::

    WEB_SEARCH_TASK
    ANALYZE_MOVIE_TASK

.. latex:clearpage::

*********
``Agent``
*********

A Select AI Agent is defined using ``agent_name``, its ``attributes`` and an
optional description. The attributes must include key agent properties such as
``profile_name`` which specifies the LLM profile used for prompt generation
and ``role``, which outlines the agent’s intended role and behavioral context.

The agent profile supplies the model used for planning and reasoning. The role
should describe the agent's domain, boundaries, and expected behavior. Keep the
role specific to the tasks assigned to the agent.

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
   :lines: 14-

output::

    Created Agent: Agent(agent_name=MOVIE_ANALYST,
    attributes=AgentAttributes(profile_name='LLAMA_4_MAVERICK',
    role='You are an AI Movie Analyst.
    Your can help answer a variety of questions related to movies. ',
    enable_human_tool=False), description=None)


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

Currently, ``process="sequential"`` is used to execute task assignments in
order. Reuse the same agent in multiple team entries when the agent should
perform multiple tasks.

For example:

.. code-block:: python

   attributes = TeamAttributes(
       agents=[
           {"name": "MOVIE_ANALYST", "task": "ANALYZE_MOVIE_TASK"},
           {"name": "MOVIE_ANALYST", "task": "SUMMARIZE_MOVIE_TASK"},
       ],
       process="sequential",
   )

.. autoclass:: select_ai.agent.TeamAttributes
   :members:

.. latex:clearpage::

.. autoclass:: select_ai.agent.Team
   :members:

.. latex:clearpage::

Run Team
++++++++

``Team.run(...)`` starts the team workflow. The ``prompt`` argument is passed to
the task and can be referenced by task instructions using ``{query}``.
``params`` can include ``conversation_id`` to associate multiple runs with the
same conversation and ``variables`` to pass additional key-value inputs.

.. code-block:: python

   result = team.run(
       prompt="Could you list the movies in the database?",
       params={
           "conversation_id": conversation_id,
           "variables": {"audience": "analyst"},
       },
   )

.. literalinclude:: ../../../samples/agent/team_create.py
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

``Team.export_team()`` returns the specification as a JSON string by default.
``Team.import_team()`` accepts either that JSON string or a Python mapping
containing the same team definition structure. In most cases, pass a ``dict``,
for example the result of ``json.loads(exported_spec)``. Other
JSON-serializable `collections.abc.Mapping <https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping>`__
objects, such as ``OrderedDict``, can also be used. On import,
``profile_name`` identifies the Select AI profile to use in the target
database. ``team_name`` can be provided to create the imported team under a new
name; this is useful when importing into the same database as the source team.

If imported object names conflict with existing agents, tasks, tools, or teams,
set ``force=True`` to let the database replace the conflicting objects. Use this
carefully when importing into a shared schema because conflicting components can
be dropped and recreated.

.. literalinclude:: ../../../samples/agent/team_export_import.py
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
    Imported team: Team(team_name=IMPORTED_MOVIE_AGENT_TEAM, ...)

The same APIs can also read from or write to object storage by passing both
``object_storage_credential_name`` and ``location``. When exporting to object
storage, ``Team.export_team()`` writes the specification to the location and
returns ``None``. When importing from object storage, pass the same credential
and location instead of ``specification``.

Lifecycle helpers
+++++++++++++++++

All agent object types support list, fetch, enable, disable, and delete
operations.

.. code-block:: python

   for tool in select_ai.agent.Tool.list():
       print(tool.tool_name)

   task = select_ai.agent.Task.fetch("ANALYZE_MOVIE_TASK")
   agent = select_ai.agent.Agent.fetch("MOVIE_ANALYST")
   team = select_ai.agent.Team.fetch("MOVIE_AGENT_TEAM")

   team.disable()
   team.enable()
   team.delete(force=True)

.. latex:clearpage::

*****************
AI agent examples
*****************

Web Search Agent using OpenAI's GPT model
+++++++++++++++++++++++++++++++++++++++++

.. literalinclude:: ../../../samples/agent/websearch_agent.py
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

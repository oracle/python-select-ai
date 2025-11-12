.. _async_agent:

``select_ai.agent`` also provides async interfaces to be used with
``async`` / ``await`` keywords

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
                                             slack_channel=None,
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

.. latex:clearpage::

Run Team
++++++++

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

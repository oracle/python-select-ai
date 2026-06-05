.. _actions:

An action in Select AI is a keyword that instructs Select AI to perform
different behavior when acting on the prompt.

Most applications use the convenience methods on ``Profile`` or
``AsyncProfile``, such as ``show_sql()``, ``run_sql()``, ``narrate()``, and
``chat()``. Use ``generate(..., action=...)`` when you want to choose the
action dynamically at runtime.

The default action for ``generate()`` is ``select_ai.Action.RUNSQL``.

********************
Supported Actions
********************

The following actions can be performed using ``select_ai``:

.. list-table:: Select AI Actions
   :header-rows: 1
   :widths: 20 30 50
   :align: left

   * - Action
     - Enum
     - Description
   * - chat
     - ``select_ai.Action.CHAT``
     - Enables general conversations with the LLM, potentially for clarifying
       prompts, exploring data, or generating content.
   * - explainsql
     - ``select_ai.Action.EXPLAINSQL``
     - Explains the generated SQL query.
   * - narrate
     - ``select_ai.Action.NARRATE``
     - Executes generated SQL and explains the output in natural language.
   * - runsql
     - ``select_ai.Action.RUNSQL``
     - Executes SQL generated from a natural language prompt. This is the
       default action for ``generate()``.
   * - showprompt
     - ``select_ai.Action.SHOWPROMPT``
     - Shows the prompt sent to the LLM.
   * - showsql
     - ``select_ai.Action.SHOWSQL``
     - Displays the generated SQL statement without executing it.
   * - summarize
     - ``select_ai.Action.SUMMARIZE``
     - Generates a summary of inline content or content referenced by a URI.
   * - feedback
     - ``select_ai.Action.FEEDBACK``
     - Provides feedback to improve the accuracy of generated SQL.
   * - translate
     - ``select_ai.Action.TRANSLATE``
     - Translates text from one language to another.

Action methods
==============

.. list-table:: Action to method mapping
   :header-rows: 1
   :widths: 30 35 35
   :align: left

   * - Action
     - Convenience method
     - Return type
   * - ``RUNSQL``
     - ``profile.run_sql(prompt)``
     - ``pandas.DataFrame``
   * - ``SHOWSQL``
     - ``profile.show_sql(prompt)``
     - ``str``
   * - ``EXPLAINSQL``
     - ``profile.explain_sql(prompt)``
     - ``str``
   * - ``NARRATE``
     - ``profile.narrate(prompt)``
     - ``str``
   * - ``CHAT``
     - ``profile.chat(prompt)``
     - ``str``
   * - ``SHOWPROMPT``
     - ``profile.show_prompt(prompt)``
     - ``str``
   * - ``SUMMARIZE``
     - ``profile.summarize(...)``
     - ``str``
   * - ``TRANSLATE``
     - ``profile.translate(...)``
     - ``str``

Choosing an action
==================

Use ``show_sql`` before ``run_sql`` when you want to inspect generated SQL
before executing it. Use ``run_sql`` when the application should return a
tabular result. Use ``narrate`` when users need a natural language answer
instead of a table. Use ``explain_sql`` and ``show_prompt`` when tuning profile
attributes, object lists, comments, constraints, or feedback.

Examples
========

Use a convenience method:

.. code-block:: python

   profile = select_ai.Profile(profile_name="oci_ai_profile")
   sql = profile.show_sql(prompt="How many promotions?")

Use ``generate`` with an explicit action:

.. code-block:: python

   profile = select_ai.Profile(profile_name="oci_ai_profile")

   sql = profile.generate(
       prompt="How many promotions?",
       action=select_ai.Action.SHOWSQL,
   )

   df = profile.generate(
       prompt="How many promotions?",
       action=select_ai.Action.RUNSQL,
   )

Use an action selected at runtime:

.. code-block:: python

   action = select_ai.Action("showsql")
   result = profile.generate(
       prompt="How many promotions?",
       action=action,
   )

Streaming
=========

Streaming is supported for text-returning generation actions:
``CHAT``, ``NARRATE``, ``EXPLAINSQL``, ``SHOWSQL``, and ``SHOWPROMPT``.
Streaming is not supported for ``RUNSQL`` because it returns a
``pandas.DataFrame``.

.. code-block:: python

   for chunk in profile.generate(
       prompt="What is OCI?",
       action=select_ai.Action.CHAT,
       stream=True,
       chunk_size=4096,
   ):
       print(chunk, end="")

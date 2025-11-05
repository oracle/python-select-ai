.. _actions:

An action in Select AI is a keyword that instructs Select AI to perform different behavior when acting on the prompt.

********************
Supported Actions
********************

Following list of actions can be performed using ``select_ai``

.. list-table:: Select AI Actions
    :header-rows: 1
    :widths: 20 30 50
    :align: left

    * - Actions
      - Enum
      - Description
    * - chat
      - ``select_ai.Action.CHAT``
      - Enables general conversations with the LLM, potentially for clarifying prompts, exploring data, or generating content.
    * - explainsql
      - ``select_ai.Action.EXPLAINSQL``
      - Explain the generated SQL query
    * - narrate
      - ``select_ai.Action.NARRATE``
      - Explains the output of the query in natural language, making the results accessible to users without deep technical expertise.
    * - runsql
      - ``select_ai.Action.RUNSQL``
      - Executes a SQL query generated from a natural language prompt. This is the default action.
    * - showprompt
      - ``select_ai.Action.SHOWPROMPT``
      - Show the details of the prompt sent to LLM
    * - showsql
      - ``select_ai.Action.SHOWSQL``
      - Displays the generated SQL statement without executing it.
    * - summarize
      - ``select_ai.Action.SUMMARIZE``
      - Generate summary of your large texts
    * - feedback
      - ``select_ai.Action.FEEDBACK``
      - Provide feedback to improve accuracy of the generated SQL
    * - translate
      - ``select_ai.Action.TRANSLATE``
      - Translate text from one language to another

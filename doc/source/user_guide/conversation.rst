.. _conversation:

Conversations in Select AI represent an interactive exchange between the user
and the system, enabling users to query or interact with the database through
a series of natural language prompts.

A conversation is stored in the database and identified by a
``conversation_id``. Pass that conversation to ``Profile.chat_session()`` or
``AsyncProfile.chat_session()`` when follow-up prompts should use prior prompts
as context. This is useful for chat workflows where the user asks a question,
then asks follow-up questions such as "explain that further" or "show another
example".

Use conversations when you need context across multiple prompts. For one-off
prompts, call profile methods such as ``chat()``, ``show_sql()``, or
``narrate()`` directly without creating a conversation.

The usual lifecycle is:

1. Create ``ConversationAttributes`` with a title, optional description,
   retention period, and conversation length.
2. Create a ``Conversation`` or ``AsyncConversation`` object.
3. Use the conversation in ``profile.chat_session(...)``.
4. List, fetch, or update the conversation metadata when needed.
5. Delete the conversation when the stored history is no longer needed.

*****************************
``Conversation Object model``
*****************************
.. _conversationfig:

.. only:: html

   .. figure:: /image/conversation_object_model.svg
      :alt: Select AI Conversation object model
      :width: 100%

.. only:: latex

   .. figure:: /image/conversation_object_model.png
      :alt: Select AI Conversation object model
      :width: 100%

.. latex:clearpage::

**************************
``ConversationAttributes``
**************************

``ConversationAttributes`` controls the metadata and retention behavior for a
conversation:

.. list-table::
   :header-rows: 1

   * - Attribute
     - Use
   * - ``title``
     - Human-readable conversation title. If omitted, the default is
       ``"New Conversation"``.
   * - ``description``
     - Optional description of the conversation topic.
   * - ``retention_days``
     - Number of days to keep the conversation in the database from its
       creation date. Use ``datetime.timedelta(days=...)``. A value of
       ``datetime.timedelta(days=0)`` keeps the conversation until it is
       manually deleted.
   * - ``conversation_length``
     - Number of prompts retained in the conversation context. The default is
       ``10``.

Example:

.. code-block:: python

   import datetime

   attributes = select_ai.ConversationAttributes(
       title="Sales analysis",
       description="Follow-up questions about quarterly sales",
       retention_days=datetime.timedelta(days=14),
       conversation_length=20,
   )

.. autoclass:: select_ai.ConversationAttributes
   :members:

.. latex:clearpage::

********************
``Conversation`` API
********************

.. autoclass:: select_ai.Conversation
   :members:

The synchronous API is used with ``select_ai.connect()`` or
``select_ai.create_pool()``. Important methods:

.. list-table::
   :header-rows: 1

   * - Method
     - Use
   * - ``create()``
     - Create a database conversation and return its ``conversation_id``.
   * - ``fetch(conversation_id)``
     - Build a ``Conversation`` object from an existing database conversation.
   * - ``get_attributes()``
     - Read conversation metadata from the database.
   * - ``set_attributes(attributes)``
     - Update the title, description, retention period, or conversation
       length.
   * - ``list()``
     - Iterate over conversations visible to the current user.
   * - ``list_prompts()``
     - Iterate over prompts and responses stored in this conversation.
   * - ``delete_prompt(conversation_prompt_id, force=False)``
     - Delete one stored prompt. Use ``force=True`` to ignore a missing prompt.
   * - ``add_tag(tag_key, tag_value)``
     - Add a tag or update the value for an existing tag key.
   * - ``remove_tag(tag_key, force=False)``
     - Remove a tag. Use ``force=True`` to ignore a missing tag.
   * - ``delete(force=False)``
     - Drop the conversation. Use ``force=True`` to ignore missing-conversation
       errors.

``Profile.chat_session(conversation=..., delete=False)`` is a context manager.
If the conversation has attributes but no ``conversation_id``, the session
creates it automatically. While the context manager is active, every
``session.chat(...)`` call passes the same ``conversation_id`` to Select AI, so
follow-up prompts can use the conversation history. If ``delete=True``, the
conversation is deleted when the session exits.

.. latex:clearpage::

Create conversation
+++++++++++++++++++

.. literalinclude:: ../../../samples/conversation_create.py
   :language: python
   :lines: 15-

output::

    Created conversation with conversation id:  3AB2ED3E-7E52-8000-E063-BE1A000A15B6

.. latex:clearpage::

Chat session
+++++++++++++

Use ``chat_session()`` to keep context across multiple chat prompts. The second
prompt in this example can refer to the previous answer because both prompts use
the same database conversation.

.. literalinclude:: ../../../samples/conversation_chat_session.py
   :language: python
   :lines: 14-

output::

    Conversation ID for this session is: 380A1910-5BF2-F7A1-E063-D81A000A3FDA

    The importance of the history of science lies in its ability to provide a comprehensive understanding of the development of scientific knowledge and its impact on society. Here are some key reasons why the history of science is important:

    1. **Contextualizing Scientific Discoveries**: The history of science helps us understand the context in which scientific discoveries were made, including the social, cultural, and intellectual climate of the time. This context is essential for appreciating the significance and relevance of scientific findings.

    ..
    ..

    The history of science is replete with examples of mistakes, errors, and misconceptions that have occurred over time. By studying these mistakes, scientists and researchers can gain valuable insights into the pitfalls and challenges that have shaped the development of scientific knowledge. Learning from past mistakes is essential for several reasons:
    ...
    ...

.. latex:clearpage::

Prompt history and tags
+++++++++++++++++++++++

``Conversation.list_prompts()`` returns an iterator of
``ConversationPrompt`` objects in creation order. Each object includes the
prompt identifier, prompt text, response text, conversation metadata, and
timestamps. Use the identifier with ``Conversation.delete_prompt()`` to remove
a stored prompt from the conversation.

Conversation tags are key-value pairs. ``Conversation.add_tag()`` creates a tag
or updates the value for an existing key. ``Conversation.remove_tag()`` removes
a tag; pass ``force=True`` when a missing tag should not raise an error.

.. autoclass:: select_ai.ConversationPrompt
   :members:

.. code-block:: python

   conversation.add_tag("PROJECT", "SELECT_AI")
   prompts = list(conversation.list_prompts())
   for prompt in prompts:
       print(prompt.conversation_prompt_id, prompt.prompt)
   conversation.delete_prompt(prompts[-1].conversation_prompt_id)
   conversation.remove_tag("PROJECT")

The complete sample creates a conversation, stores one prompt through a chat
session, lists the resulting ``ConversationPrompt``, deletes it, and exercises
tag creation, update, and removal:

.. literalinclude:: ../../../samples/conversation_prompts_tags.py
   :language: python
   :lines: 14-

The conversation ID, prompt ID, and model response vary between runs.
Representative output is:

output::

    conversation history works.
    Prompt <generated prompt id>: Reply with exactly: conversation history works.
    Prompts after deletion: []

.. latex:clearpage::

List conversations
++++++++++++++++++

Listing returns ``Conversation`` objects with their ``conversation_id`` and
metadata. It does not replay the conversation transcript.

.. literalinclude:: ../../../samples/conversations_list.py
   :language: python
   :lines: 14-

output::

    5275A80-A290-DA17-E063-151B000AD3B4
    ConversationAttributes(title='History of Science', description="LLM's understanding of history of science", retention_days=7)

    37DF777F-F3DA-F084-E063-D81A000A53BE
    ConversationAttributes(title='History of Science', description="LLM's understanding of history of science", retention_days=7)

.. latex:clearpage::

Delete conversation
+++++++++++++++++++

Delete conversations that are no longer needed, especially when
``retention_days`` is set to ``0`` or when the content should not remain in the
database after a session ends. For temporary sessions, prefer
``profile.chat_session(conversation=conversation, delete=True)``.

.. literalinclude:: ../../../samples/conversation_delete.py
   :language: python
   :lines: 14-

output::

    Deleted conversation with conversation id:  37DDC22E-11C8-3D49-E063-D81A000A85FE


.. latex:clearpage::

*************************
``AsyncConversation`` API
*************************

.. autoclass:: select_ai.AsyncConversation
   :members:

The async API mirrors the synchronous API and is used with
``select_ai.async_connect()`` or ``select_ai.create_pool_async()``.

.. list-table::
   :header-rows: 1

   * - Synchronous API
     - Async API
   * - ``Conversation.create()``
     - ``await AsyncConversation.create()``
   * - ``Conversation.fetch(...)``
     - ``await AsyncConversation.fetch(...)``
   * - ``Conversation.get_attributes()``
     - ``await AsyncConversation.get_attributes()``
   * - ``Conversation.set_attributes(...)``
     - ``await AsyncConversation.set_attributes(...)``
   * - ``for conversation in Conversation.list()``
     - ``async for conversation in AsyncConversation.list()``
   * - ``Conversation.delete(...)``
     - ``await AsyncConversation.delete(...)``
   * - ``Conversation.list_prompts()``
     - ``async for prompt in AsyncConversation.list_prompts()``
   * - ``Conversation.delete_prompt(...)``
     - ``await AsyncConversation.delete_prompt(...)``
   * - ``Conversation.add_tag(...)``
     - ``await AsyncConversation.add_tag(...)``
   * - ``Conversation.remove_tag(...)``
     - ``await AsyncConversation.remove_tag(...)``
   * - ``with profile.chat_session(...)``
     - ``async with async_profile.chat_session(...)``

.. latex:clearpage::

Async chat session
++++++++++++++++++

Use ``AsyncProfile.chat_session()`` in async applications. The conversation is
created automatically when the object has attributes and no ``conversation_id``.

.. literalinclude:: ../../../samples/async/conversation_chat_session.py
   :language: python
   :lines: 13-

output::

    Conversation ID for this session is: 380A1910-5BF2-F7A1-E063-D81A000A3FDA

    The importance of the history of science lies in its ability to provide a comprehensive understanding of the development of scientific knowledge and its impact on society. Here are some key reasons why the history of science is important:

    1. **Contextualizing Scientific Discoveries**: The history of science helps us understand the context in which scientific discoveries were made, including the social, cultural, and intellectual climate of the time. This context is essential for appreciating the significance and relevance of scientific findings.

    ..
    ..

    The history of science is replete with examples of mistakes, errors, and misconceptions that have occurred over time. By studying these mistakes, scientists and researchers can gain valuable insights into the pitfalls and challenges that have shaped the development of scientific knowledge. Learning from past mistakes is essential for several reasons:
    ...
    ...

.. latex:clearpage::

Async prompt history and tags
+++++++++++++++++++++++++++++

``AsyncConversation.list_prompts()`` is an async generator that yields the same
``ConversationPrompt`` objects as the synchronous API. Await
``delete_prompt()``, ``add_tag()``, and ``remove_tag()`` to manage stored
prompts and conversation tags. As with the synchronous API, use ``force=True``
when deleting a missing prompt or removing a missing tag should succeed.

.. code-block:: python

   await conversation.add_tag("PROJECT", "SELECT_AI")
   prompts = [prompt async for prompt in conversation.list_prompts()]
   for prompt in prompts:
       print(prompt.conversation_prompt_id, prompt.prompt)
   await conversation.delete_prompt(prompts[-1].conversation_prompt_id)
   await conversation.remove_tag("PROJECT")

The asynchronous sample performs the same prompt-history and tag-management
flow using ``AsyncConversation``:

.. literalinclude:: ../../../samples/async/conversation_prompts_tags.py
   :language: python
   :lines: 13-

The conversation ID, prompt ID, and model response vary between runs.
Representative output is:

output::

    conversation history works.
    Prompt <generated prompt id>: Reply with exactly: conversation history works.
    Prompts after deletion: []

.. latex:clearpage::

Async list conversations
++++++++++++++++++++++++

``AsyncConversation.list()`` is an async iterator.

.. literalinclude:: ../../../samples/async/conversations_list.py
   :language: python
   :lines: 14-

output::

    5275A80-A290-DA17-E063-151B000AD3B4
    ConversationAttributes(title='History of Science', description="LLM's understanding of history of science", retention_days=7)

    37DF777F-F3DA-F084-E063-D81A000A53BE
    ConversationAttributes(title='History of Science', description="LLM's understanding of history of science", retention_days=7)

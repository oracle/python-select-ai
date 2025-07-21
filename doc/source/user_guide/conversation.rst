.. _conversation:

Conversations in Select AI represent an interactive exchange between the user and the system, enabling users to query or interact with the database through a series of natural language prompts.

*****************************
``Conversation Object model``
*****************************
.. _conversationfig:
.. figure:: /image/conversation.png
   :alt: Select AI Conversation

**************************
``ConversationAttributes``
**************************

.. autoclass:: select_ai.ConversationAttributes
   :members:


********************
``Conversation`` API
********************

.. autoclass:: select_ai.Conversation
   :members:

Create conversion
++++++++++++++++++

.. literalinclude:: ../../../samples/conversation_create.py
   :language: python

output::

    Created conversation with conversation id:  380A1601-182D-F329-E063-D81A000A2C93

Chat session
+++++++++++++

.. literalinclude:: ../../../samples/conversation_chat_session.py
   :language: python

output::

    Conversation ID for this session is: 380A1910-5BF2-F7A1-E063-D81A000A3FDA

    The importance of the history of science lies in its ability to provide a comprehensive understanding of the development of scientific knowledge and its impact on society. Here are some key reasons why the history of science is important:

    1. **Contextualizing Scientific Discoveries**: The history of science helps us understand the context in which scientific discoveries were made, including the social, cultural, and intellectual climate of the time. This context is essential for appreciating the significance and relevance of scientific findings.

    ..
    ..

    The history of science is replete with examples of mistakes, errors, and misconceptions that have occurred over time. By studying these mistakes, scientists and researchers can gain valuable insights into the pitfalls and challenges that have shaped the development of scientific knowledge. Learning from past mistakes is essential for several reasons:
    ...
    ...

List conversations
++++++++++++++++++

.. literalinclude:: ../../../samples/conversations_list.py
   :language: python

output::

    5275A80-A290-DA17-E063-151B000AD3B4
    ConversationAttributes(title='History of Science', description="LLM's understanding of history of science", retention_days=7)

    37DF777F-F3DA-F084-E063-D81A000A53BE
    ConversationAttributes(title='History of Science', description="LLM's understanding of history of science", retention_days=7)


Delete conversation
+++++++++++++++++++

.. literalinclude:: ../../../samples/conversation_delete.py
   :language: python

output::

    Deleted conversation with conversation id:  37DDC22E-11C8-3D49-E063-D81A000A85FE



*************************
``AsyncConversation`` API
*************************

.. autoclass:: select_ai.AsyncConversation
   :members:


Async chat session
++++++++++++++++++

.. literalinclude:: ../../../samples/async_samples/conversation_chat_session.py
   :language: python

output::

    Conversation ID for this session is: 380A1910-5BF2-F7A1-E063-D81A000A3FDA

    The importance of the history of science lies in its ability to provide a comprehensive understanding of the development of scientific knowledge and its impact on society. Here are some key reasons why the history of science is important:

    1. **Contextualizing Scientific Discoveries**: The history of science helps us understand the context in which scientific discoveries were made, including the social, cultural, and intellectual climate of the time. This context is essential for appreciating the significance and relevance of scientific findings.

    ..
    ..

    The history of science is replete with examples of mistakes, errors, and misconceptions that have occurred over time. By studying these mistakes, scientists and researchers can gain valuable insights into the pitfalls and challenges that have shaped the development of scientific knowledge. Learning from past mistakes is essential for several reasons:
    ...
    ...

Async list conversations
++++++++++++++++++++++++

.. literalinclude:: ../../../samples/async_samples/conversations_list.py
   :language: python

output::

    5275A80-A290-DA17-E063-151B000AD3B4
    ConversationAttributes(title='History of Science', description="LLM's understanding of history of science", retention_days=7)

    37DF777F-F3DA-F084-E063-D81A000A53BE
    ConversationAttributes(title='History of Science', description="LLM's understanding of history of science", retention_days=7)

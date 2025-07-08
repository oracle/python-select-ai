.. _conversation:

********************
``Conversation``
********************

.. autoclass:: select_ai.Conversation
   :members:

*********************
``AsyncConversation``
*********************

.. autoclass:: select_ai.AsyncConversation
   :members:

**************************
``ConversationAttributes``
**************************

.. autoclass:: select_ai.ConversationAttributes
   :members:

************
Conversation
************

Create conversion
++++++++++++++++++

.. literalinclude:: ../../../examples/conversation_create.py
   :language: python

output::

    Created conversation with conversation id:  380A1601-182D-F329-E063-D81A000A2C93

Chat session
+++++++++++++

.. literalinclude:: ../../../examples/conversation_chat_session.py
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

.. literalinclude:: ../../../examples/conversations_list.py
   :language: python

output::

    5275A80-A290-DA17-E063-151B000AD3B4
    ConversationAttributes(title='History of Science', description="LLM's understanding of history of science", retention_days=7)

    37DF777F-F3DA-F084-E063-D81A000A53BE
    ConversationAttributes(title='History of Science', description="LLM's understanding of history of science", retention_days=7)


Delete conversation
+++++++++++++++++++

.. literalinclude:: ../../../examples/conversation_delete.py
   :language: python

output::

    Deleted conversation with conversation id:  37DDC22E-11C8-3D49-E063-D81A000A85FE


*********************
Async conversation
*********************


Chat Session
+++++++++++++

.. literalinclude:: ../../../examples/async_examples/conversation_chat_session.py
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

.. literalinclude:: ../../../examples/async_examples/conversations_list.py
   :language: python

output::

    5275A80-A290-DA17-E063-151B000AD3B4
    ConversationAttributes(title='History of Science', description="LLM's understanding of history of science", retention_days=7)

    37DF777F-F3DA-F084-E063-D81A000A53BE
    ConversationAttributes(title='History of Science', description="LLM's understanding of history of science", retention_days=7)

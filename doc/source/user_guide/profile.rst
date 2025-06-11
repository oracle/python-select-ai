.. _profile:

An AI profile is a specification that includes the AI provider to use and other
details regarding metadata and database objects required for generating
responses to natural language prompts.

An AI profile object can be created using ``select_ai.Profile()``

*******************************
Base ``Profile`` methods
*******************************
.. autoclass:: select_ai.BaseProfile
   :members:

*******************************
Synchronous ``Profile`` methods
*******************************

.. autoclass:: select_ai.Profile
   :members:

**************************
Enable AI service provider
**************************

.. literalinclude:: ../../../examples/1_enable_ai_provider.py
   :language: python


**************************
Create credential
**************************

.. literalinclude:: ../../../examples/2_create_ai_credential.py
   :language: python


**************************
Show SQL
**************************

.. literalinclude:: ../../../examples/3_show_sql.py
   :language: python

**************************
Run SQL
**************************

.. literalinclude:: ../../../examples/4_run_sql.py
   :language: python

**************************
Chat
**************************

.. literalinclude:: ../../../examples/5_chat.py
   :language: python

**************************
List profiles
**************************

.. literalinclude:: ../../../examples/6_list_ai_profiles.py
   :language: python


***************************
Disable AI service provider
***************************

.. literalinclude:: ../../../examples/10_disable_ai_provider.py
   :language: python

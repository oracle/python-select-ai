.. _release-1-5-0:

*******************
What's new in 1.5.0
*******************

Version 1.5.0 adds A2A integration, object sharing, request-level profile
overrides, and typed agent history APIs. The changes below are relative to
1.4.1.

New and expanded APIs
=====================

* Expose an agent team with the optional :ref:`A2A server <a2a>`. Choose fixed
  or dynamic connections and standalone or clustered deployment. A2A includes
  Oracle-backed task/context storage, task polling, A2UI connection forms, and
  A2A 1.0/v0.3 JSON-RPC compatibility.
* :ref:`Share profiles, vector indexes, teams, and credentials <sharing>`
  with database users or roles. Profile and vector-index fetch/list APIs
  accept ``owner`` and expose ``qualified_name``.
* Pass an ``attributes`` mapping to profile and session actions for
  :ref:`request-only overrides <request-profile-attributes>`. Async pipelines
  can apply the same override mapping to every operation.
* Inspect agent execution with :ref:`TeamHistory, TaskHistory, and ToolHistory
  <user_guide/agent:Agent history>` and their async equivalents.
* Enable and disable profiles without deleting them. Configure
  ``additional_instructions``, integer ``seed``, and translation language
  defaults with ``ProfileAttributes``. Per-call translation languages are
  optional and can use the saved defaults.
* Configure supervised teams with ``AgentAttributes.supervisor`` and
  ``TeamAttributes.supervisor_agent``; inspect the database-generated
  ``supervisor_task`` after creation.

Upgrade considerations
======================

* **Python 3.11 is now the minimum.** Python 3.9 and 3.10 are no longer
  supported. Supported versions are 3.11 through 3.14.
* **pandas is now pinned to 3.0.3**, replacing 2.2.3. Check applications that
  consume DataFrames for pandas compatibility when upgrading.
* ``ProfileAttributes.seed`` is now typed as an integer. Supply an integer
  rather than a numeric string.
* Unspecified ``SyntheticDataParams`` values are omitted so the database can
  apply its defaults. Set values explicitly if your application relies on
  particular generation settings.
* Install ``select_ai[a2a]`` to use A2A commands; ``select_ai[cli]`` covers
  the other CLI commands. Prepare A2A database storage privileges as described
  in :ref:`A2A prerequisites <user_guide/a2a:Installation and prerequisites>`.
* ``--require-oauth`` requires a bearer token and derives an owner scope.
  Token signatures and claims must be validated by a trusted upstream service;
  the SDK flag alone does not verify identity. See :ref:`A2A authentication
  <user_guide/a2a:End-user OAuth and session ownership>`.

Upgrade in your application's virtual environment:

.. code-block:: bash

   python -m pip install --upgrade 'select_ai==1.5.0'
   # If you use A2A:
   python -m pip install --upgrade 'select_ai[a2a]==1.5.0'

See :ref:`Compatibility <compatibility>` for the feature requirements and
:ref:`Run your first SQL query <first-query>` for a complete example.

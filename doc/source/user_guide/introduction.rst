.. _introduction:

*****************************************************
Introduction to Select AI for Python
*****************************************************

``select_ai`` is a Python module that helps you invoke `DBMS_CLOUD_AI <https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/dbms-cloud-ai-package.html>`__
using Python. It supports text-to-SQL generation, retrieval augmented generation
(RAG), synthetic data generation, and several other features using Oracle-based
and third-party AI providers.

Select AI for Python bridges Oracle Database's Select AI capabilities and the
Python ecosystem. It gives Python applications a higher-level API for working
with AI providers, credentials, profiles, natural language prompts, vector
indexes, conversations, summarization, synthetic data, and AI agent workflows.

.. only:: html

   .. figure:: /image/select_ai_a2a_server_demo.gif
      :alt: Select AI A2A server demo from the project README
      :width: 100%

      Connect an A2A client to a Select AI agent team. Follow the
      :ref:`A2A guide <a2a>` to run the server.

For a complete setup-to-query example, start with :ref:`Run your first SQL
query <first-query>`. Existing users can review :ref:`What's new in 1.5.0
<release-1-5-0>` and :ref:`Compatibility <compatibility>`.

What you can build
==================

Start with the workflow you want to build:

* **Natural language data apps:** generate SQL, return query results as pandas
  DataFrames, or explain results in plain language with :ref:`Profiles <profile>`
  and :ref:`Async Profiles <async_profile>`.
* **RAG and chat assistants:** ground answers in your documents with
  :ref:`Vector Indexes <vector_index>` and keep chat context with
  :ref:`Conversations <conversation>`.
* **AI agent workflows:** compose tools, tasks, and agents into
  :ref:`Teams <agent>`, then expose a team to other AI applications through
  an :ref:`Agent2Agent (A2A) server <a2a>`.
* **Python web services:** add Select AI endpoints to FastAPI, Flask, or Django
  using the pool lifecycle patterns in :ref:`Web Frameworks <web_frameworks>`.
* **Concurrent prompt processing:** use threads, async tasks, queues, or a
  database pipeline with the :ref:`Concurrency Guides <concurrent_prompt_processing>`.
* **Content and test-data tools:** :ref:`summarize content <summary>`,
  :ref:`translate text <user_guide/profile:Translate>`, or generate
  :ref:`Synthetic Data <synthetic_data>` for database tables.
* **Terminal workflows:** chat, generate SQL, and run an A2A server with the
  optional :ref:`Command Line Interface <cli>`.

Core concepts
=============

Most workflows use the same building blocks:

.. list-table::
   :header-rows: 1

   * - Concept
     - Purpose
     - Start here
   * - Connection
     - Connect to Oracle Database using a standalone connection or a pool.
     - :ref:`Connection <conn>`
   * - Privileges
     - Grant package privileges and network ACLs required for Select AI calls.
     - :ref:`Privileges <privileges>`
   * - Provider
     - Describe the AI service, model, endpoint, region, or provider-specific
       options.
     - :ref:`Provider <provider>`
   * - Credential
     - Store provider and service secrets securely in Oracle Database.
     - :ref:`Credential <credential>`
   * - Sharing and ownership
     - Share profiles, vector indexes, teams, and credentials with users or
       roles and address objects owned by another schema.
     - :ref:`Sharing and ownership <sharing>`
   * - Profile
     - Combine provider, credential, database object scope, and generation
       options into a reusable Select AI profile.
     - :ref:`Profile <profile>`
   * - Actions
     - Choose what Select AI should do with a prompt, such as show SQL, run
       SQL, chat, narrate, summarize, or translate.
     - :ref:`Actions <actions>`
   * - Conversation
     - Keep prompt history for context-aware chat sessions.
     - :ref:`Conversation <conversation>`
   * - Vector index
     - Index document content for RAG over trusted source material.
     - :ref:`Vector Index <vector_index>`
   * - Agent
     - Define tools, tasks, agents, and teams for multi-step AI workflows.
     - :ref:`Agent <agent>`

   * - Agent2Agent (A2A)
     - Expose an agent team as a discoverable service for A2A clients. Choose
       standalone or clustered deployment and fixed or dynamic connections.
     - :ref:`A2A server <a2a>`

Synchronous and asynchronous APIs
=================================

``select_ai`` supports both synchronous and asynchronous programming styles.
Use the synchronous APIs for scripts, notebooks, command-line tools, and simple
services. Use the asynchronous APIs with ``asyncio`` applications, async web
frameworks, and workloads that need to run many prompts concurrently.

For long-running services, create a connection pool once during application
startup and close it during shutdown. See :ref:`Connection <conn>`,
:ref:`Web Frameworks <web_frameworks>`, and
:ref:`Concurrent Prompt Processing <concurrent_prompt_processing>` for
patterns.

Supported Python versions
=========================

The Select AI Python API supports Python versions 3.11, 3.12, 3.13, and 3.14.

.. latex:clearpage::

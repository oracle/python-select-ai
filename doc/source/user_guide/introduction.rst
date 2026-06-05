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

What you can build
==================

Use ``select_ai`` to:

* Ask questions about database objects in natural language and generate SQL.
* Run generated SQL and return results as Python objects such as pandas data
  frames.
* Generate narrative answers, explanations, prompt previews, translations, and
  summaries.
* Use Retrieval Augmented Generation (RAG) with vector indexes over documents
  and object storage content.
* Create synthetic data for database tables.
* Build context-aware chat sessions with database-backed conversations.
* Register tools, tasks, agents, and teams for database-backed AI agent
  workflows.
* Use the optional ``select-ai`` command line interface for interactive chat
  and SQL workflows.
* Use synchronous APIs, asynchronous APIs, and connection pools in scripts,
  services, and web applications.

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

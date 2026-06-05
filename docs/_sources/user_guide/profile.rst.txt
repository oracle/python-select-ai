.. _profile:

An AI profile is a specification that includes the AI provider to use and other
details regarding metadata and database objects required for generating
responses to natural language prompts.

An AI profile object can be created using ``select_ai.Profile()``. Creating a
profile stores the profile in Oracle Database. Later, you can instantiate
``select_ai.Profile(profile_name="...")`` to reuse an existing database profile
without passing all attributes again.

Before creating a profile, make sure the database user has the required
privileges, a credential for the AI provider, network access to the provider
endpoint, and access to the database objects included in the profile. See
:ref:`Privileges <privileges>`, :ref:`Credential <credential>`,
:ref:`Provider <provider>`, and
:ref:`ProfileAttributes <profile_attributes>`.

Profile lifecycle
=================

The usual profile lifecycle is:

* Create a provider object.
* Create ``ProfileAttributes`` with the provider, credential name, and object
  list.
* Create the profile with ``select_ai.Profile(...)``.
* Reuse the profile later by name.
* Update profile attributes when provider settings or object scope changes.
* Delete profiles that are no longer needed.

``replace=True`` recreates a profile when a profile with the same name already
exists. ``merge=True`` fetches the existing profile and updates it with the
non-null attributes passed by the caller.

Profile actions
===============

.. list-table:: Common profile actions
   :header-rows: 1
   :widths: 25 75
   :align: left

   * - Method
     - Description
   * - ``show_sql()``
     - Generates SQL for a natural language prompt without executing it.
   * - ``run_sql()``
     - Generates SQL, executes it, and returns a ``pandas.DataFrame``.
   * - ``narrate()``
     - Generates SQL, executes it, and returns a natural language answer.
   * - ``explain_sql()``
     - Explains the generated SQL for a prompt.
   * - ``show_prompt()``
     - Shows the prompt sent to the model.
   * - ``chat()``
     - Sends a general chat prompt to the model.
   * - ``summarize()``
     - Summarizes inline content or content referenced by a URI.
   * - ``translate()``
     - Translates text from one language to another.

********************
Profile Object Model
********************

.. _profilefig:
.. figure:: /image/profile_provider.png
   :alt: Select AI Profile and Providers

.. latex:clearpage::

*******************************
Base ``Profile`` API
*******************************
.. autoclass:: select_ai.BaseProfile
   :members:

.. latex:clearpage::

*******************************
``Profile`` API
*******************************

.. autoclass:: select_ai.Profile
   :members:

.. latex:clearpage::

**************************
Create Profile
**************************

The following example creates an OCI Gen AI profile that can generate SQL over
objects in the ``SH`` schema.

.. literalinclude:: ../../../samples/profile_create.py
   :language: python
   :lines: 14-

output::

    Created profile  oci_ai_profile
    Profile attributes are:  {'annotations': None,
     'case_sensitive_values': None,
     'comments': None,
     'constraints': None,
     'conversation': None,
     'credential_name': 'my_oci_ai_profile_key',
     'enable_source_offsets': None,
     'enable_sources': None,
     'enforce_object_list': None,
     'max_tokens': '1024',
     'object_list': '[{"owner":"SH"}]',
     'object_list_mode': None,
     'provider': OCIGenAIProvider(embedding_model=None,
                                  model=None,
                                  provider_name='oci',
                                  provider_endpoint=None,
                                  region='us-chicago-1',
                                  oci_apiformat='GENERIC',
                                  oci_compartment_id=None,
                                  oci_endpoint_id=None,
                                  oci_runtimetype=None),
     'seed': None,
     'stop_tokens': None,
     'streaming': None,
     'temperature': None,
     'vector_index_name': None}


.. latex:clearpage::

**************************
Reuse Profile
**************************

After a profile has been created, instantiate ``Profile`` with only the profile
name to reuse the database profile:

.. code-block:: python

   profile = select_ai.Profile(profile_name="oci_ai_profile")
   sql = profile.show_sql(prompt="How many promotions?")

Use ``Profile.fetch(...)`` when you want to create a proxy object from a saved
database profile and raise an error if the profile does not exist:

.. code-block:: python

   profile = select_ai.Profile.fetch("oci_ai_profile")

.. latex:clearpage::

**************************
Update Profile
**************************

Use ``set_attribute(...)`` to update one profile attribute or
``set_attributes(...)`` to update several attributes. Updates are saved to the
database profile.

.. code-block:: python

   profile = select_ai.Profile(profile_name="oci_ai_profile")
   profile.set_attribute("temperature", 0.1)

   profile.set_attributes(
       select_ai.ProfileAttributes(
           max_tokens=2048,
           enforce_object_list=True,
       )
   )

.. latex:clearpage::

**************************
Delete Profile
**************************

Use ``delete(...)`` or ``Profile.delete_profile(...)`` to remove a profile from
the database. Pass ``force=True`` when cleanup should succeed even if the
profile does not exist.

.. code-block:: python

   profile = select_ai.Profile(profile_name="oci_ai_profile")
   profile.delete(force=True)

   select_ai.Profile.delete_profile("oci_ai_profile", force=True)

.. latex:clearpage::

**************************
Narrate
**************************

.. literalinclude:: ../../../samples/profile_narrate.py
   :language: python
   :lines: 14-

output::

    There are 503 promotions in the database.


.. latex:clearpage::

**************************
Show SQL
**************************

.. literalinclude:: ../../../samples/profile_show_sql.py
   :language: python
   :lines: 14-

output::

    SELECT
    COUNT("p"."PROMO_ID") AS "Number of Promotions"
    FROM "SH"."PROMOTIONS" "p"

.. latex:clearpage::

**************************
Explain SQL
**************************

Use ``explain_sql(...)`` to generate SQL and return a natural language
explanation without executing the SQL.

.. code-block:: python

   profile = select_ai.Profile(profile_name="oci_ai_profile")
   explanation = profile.explain_sql(prompt="How many promotions?")
   print(explanation)

.. latex:clearpage::

**************************
Show Prompt
**************************

Use ``show_prompt(...)`` to inspect the prompt that Select AI sends to the
model. This is useful when tuning profile attributes, object lists, comments,
constraints, and provider settings.

.. code-block:: python

   profile = select_ai.Profile(profile_name="oci_ai_profile")
   prompt = profile.show_prompt(prompt="How many promotions?")
   print(prompt)

.. latex:clearpage::

**************************
Run SQL
**************************

.. literalinclude:: ../../../samples/profile_run_sql.py
   :language: python
   :lines: 14-

output::

    Index(['Number of Promotions'], dtype='object')
        Number of Promotions
    0                    503


.. latex:clearpage::

**************************
Chat
**************************

.. literalinclude:: ../../../samples/profile_chat.py
   :language: python
   :lines: 14-

output::

    OCI stands for Oracle Cloud Infrastructure. It is a comprehensive cloud computing platform provided by Oracle Corporation that offers a wide range of services for computing, storage, networking, database, and more.
    ...
    ...
    OCI competes with other major cloud providers, including Amazon Web Services (AWS), Microsoft Azure, Google Cloud Platform (GCP), and IBM Cloud.

.. latex:clearpage::

**************************
Streaming chat
**************************

.. literalinclude:: ../../../samples/profile_chat_stream.py
   :language: python
   :lines: 14-

``stream=True`` lets callers consume generated CLOB responses chunk by chunk,
reducing memory pressure and making it easier to progressively forward output
to files, services, or user interfaces. Streaming text APIs return an iterator
of ``str`` chunks. The ``chunk_size`` parameter controls the number of CLOB
characters read per chunk; it is not a byte count.

Streaming is supported by ``generate()``, ``chat()``, ``narrate()``,
``explain_sql()``, ``show_sql()``, and ``show_prompt()``. It is not supported
for ``run_sql()``, which returns a ``pandas.DataFrame``.

.. latex:clearpage::

**************************
Summarize
**************************

Summarize inline content

.. literalinclude:: ../../../samples/profile_summarize_content.py
   :language: python
   :lines: 14-

output::

    A gas cloud in the Sagittarius B2 galaxy contains a large amount of alcohol,
    while some stars are cool enough to touch without being burned. The exoplanet
    55 Cancri e has a unique form of "hot ice" where water remains solid despite
    high temperatures due to high pressure. Ancient stars in the Milky Way's halo
    are older than the Sun, providing insights into the early universe and its composition,
    offering clues about the universe's formation and evolution.

.. latex:clearpage::

Summarize content accessible via a URL

.. literalinclude:: ../../../samples/profile_summarize_uri.py
   :language: python
   :lines: 14-

output::

    Astronomy is a natural science that studies celestial objects and phenomena,
    using mathematics, physics, and chemistry to explain their origin and evolution.
    The field has a long history, with early civilizations making methodical
    observations of the night sky, and has since split into observational and
    theoretical branches. Observational astronomy focuses on acquiring data
    from observations, while theoretical astronomy develops computer or
    analytical models to describe astronomical objects and phenomena. The study
    of astronomy has led to numerous discoveries, including the existence of
    galaxies, the expansion of the universe, and the detection of gravitational
    waves. Astronomers use various methods, such as radio, infrared, optical,
    ultraviolet, X-ray, and gamma-ray astronomy, to study objects and events in
    the universe. The field has also led to the development of new technologies and
    has inspired new areas of research, such as astrobiology and the search for
    extraterrestrial life. Overall, astronomy is a dynamic and constantly evolving
    field that seeks to understand the universe and its many mysteries.

.. latex:clearpage::

***********
Translate
***********

.. literalinclude:: ../../../samples/profile_translate.py
   :language: python
   :lines: 14-

output::

    Danke

.. latex:clearpage::

**************************
List profiles
**************************

Profile listing returns profiles visible to the connected database user.
Instantiate ``Profile`` with one of the returned names to reuse the saved
profile.

.. literalinclude:: ../../../samples/profiles_list.py
   :language: python
   :lines: 14-


output::

    ASYNC_OCI_AI_PROFILE
    OCI_VECTOR_AI_PROFILE
    ASYNC_OCI_VECTOR_AI_PROFILE
    OCI_AI_PROFILE

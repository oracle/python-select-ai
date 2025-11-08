# Select AI for Python


Select AI for Python enables you to ask questions of your database data using natural language (text-to-SQL), get generative AI responses using your trusted content (retrieval augmented generation), generate synthetic data using large language models, and other features – all from Python. With the general availability of Select AI Python, Python developers have access to the functionality of Select AI on Oracle Autonomous Database.

Select AI for Python enables you to leverage the broader Python ecosystem in combination with generative AI and database functionality - bridging the gap between the DBMS_CLOUD_AI PL/SQL package and Python's rich ecosystem. It provides intuitive objects and methods for AI model interaction.


## Installation

Run
```bash
python3 -m pip install select_ai
```

## Documentation

See [Select AI for Python documentation][documentation]

## Samples

Examples can be found in the [/samples][samples] directory

### Basic Example

```python
import select_ai

user = "<your_select_ai_user>"
password = "<your_select_ai_password>"
dsn = "<your_select_ai_db_connect_string>"

select_ai.connect(user=user, password=password, dsn=dsn)
profile = select_ai.Profile(profile_name="oci_ai_profile")
# run_sql returns a pandas dataframe
df = profile.run_sql(prompt="How many promotions?")
print(df.columns)
print(df)
```

### Async Example

```python

import asyncio

import select_ai

user = "<your_select_ai_user>"
password = "<your_select_ai_password>"
dsn = "<your_select_ai_db_connect_string>"

# This example shows how to asynchronously run sql
async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    async_profile = await select_ai.AsyncProfile(
        profile_name="async_oci_ai_profile",
    )
    # run_sql returns a pandas df
    df = await async_profile.run_sql("How many promotions?")
    print(df)

asyncio.run(main())

```
## Help

Questions can be asked in [GitHub Discussions][ghdiscussions].

Problem reports can be raised in [GitHub Issues][ghissues].

## Contributing

This project welcomes contributions from the community. Before submitting a pull request, please [review our contribution guide][contributing]

## Security

Please consult the [security guide][security] for our responsible security vulnerability disclosure process

## License

Copyright (c) 2025 Oracle and/or its affiliates.

Released under the Universal Permissive License v1.0 as shown at
<https://oss.oracle.com/licenses/upl/>.

[contributing]: https://github.com/oracle/python-select-ai/blob/main/CONTRIBUTING.md
[documentation]: https://oracle.github.io/python-select-ai/
[ghdiscussions]: https://github.com/oracle/python-select-ai/discussions
[ghissues]: https://github.com/oracle/python-select-ai/issues
[samples]: https://github.com/oracle/python-select-ai/tree/main/samples
[security]: https://github.com/oracle/python-select-ai/blob/main/SECURITY.md

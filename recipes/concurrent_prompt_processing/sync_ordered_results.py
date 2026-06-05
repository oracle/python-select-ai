# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# concurrent_prompt_processing/sync_ordered_results.py
#
# Process independent prompts concurrently and keep results in input order.
# -----------------------------------------------------------------------------

import os
from concurrent.futures import ThreadPoolExecutor

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

pool_min = int(os.getenv("SELECT_AI_POOL_MIN", "1"))
pool_max = int(os.getenv("SELECT_AI_POOL_MAX", "4"))
pool_increment = int(os.getenv("SELECT_AI_POOL_INCREMENT", "1"))

profile_name = os.getenv("SELECT_AI_PROFILE_NAME", "oci_ai_profile")
max_workers = int(os.getenv("SELECT_AI_MAX_WORKERS", str(pool_max)))

prompts = [
    "How many customers?",
    "How many products?",
    "How many promotions?",
    "List the top 5 customers by sales.",
]


def show_sql(prompt):
    profile = select_ai.Profile(profile_name=profile_name)
    return profile.show_sql(prompt=prompt)


select_ai.create_pool(
    user=user,
    password=password,
    dsn=dsn,
    min_size=pool_min,
    max_size=pool_max,
    increment=pool_increment,
)

try:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(show_sql, prompts)

        for prompt, sql in zip(prompts, results):
            print(f"\nPrompt: {prompt}")
            print(sql)
finally:
    select_ai.disconnect()

# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# concurrent_prompt_processing/sync_queue_workers.py
#
# Process prompts with synchronous queue workers.
# -----------------------------------------------------------------------------

import os
from queue import Queue
from threading import Thread

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

pool_min = int(os.getenv("SELECT_AI_POOL_MIN", "1"))
pool_max = int(os.getenv("SELECT_AI_POOL_MAX", "4"))
pool_increment = int(os.getenv("SELECT_AI_POOL_INCREMENT", "1"))

profile_name = os.getenv("SELECT_AI_PROFILE_NAME", "oci_ai_profile")
worker_count = int(os.getenv("SELECT_AI_WORKER_COUNT", str(pool_max)))

prompts = [
    "How many customers?",
    "How many products?",
    "How many promotions?",
    "List the top 5 customers by sales.",
]


def worker(queue, results):
    while True:
        item = queue.get()
        try:
            if item is None:
                return

            index, prompt = item
            profile = select_ai.Profile(profile_name=profile_name)
            sql = profile.show_sql(prompt=prompt)
            results[index] = (prompt, sql)
        finally:
            queue.task_done()


select_ai.create_pool(
    user=user,
    password=password,
    dsn=dsn,
    min_size=pool_min,
    max_size=pool_max,
    increment=pool_increment,
)

try:
    queue = Queue()
    results = [None] * len(prompts)

    workers = [
        Thread(target=worker, args=(queue, results))
        for _ in range(worker_count)
    ]
    for thread in workers:
        thread.start()

    for index, prompt in enumerate(prompts):
        queue.put((index, prompt))

    for _ in workers:
        queue.put(None)

    queue.join()
    for thread in workers:
        thread.join()

    for prompt, sql in results:
        print(f"\nPrompt: {prompt}")
        print(sql)
finally:
    select_ai.disconnect()

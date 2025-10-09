import os
from pprint import pformat

import select_ai
import select_ai.agent
from select_ai.agent import Task, TaskAttributes

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

select_ai.connect(user=user, password=password, dsn=dsn)

attributes = TaskAttributes(
    instruction="Help the user with their request about movies. "
    "User question: {query}. "
    "You can use SQL tool to search the data from database",
    tools=["MOVIE_SQL_TOOL"],
    enable_human_tool=False,
)

task = Task(
    task_name="ANALYZE_MOVIE_TASK",
    description="Movie task involving a human",
    attributes=attributes,
)

task.create(replace=True)

print(task.task_name)
print(pformat(task.attributes))

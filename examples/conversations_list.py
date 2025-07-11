# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


def main():
    select_ai.connect(user=user, password=password, dsn=dsn)
    # To list all conversations, use the class method list()
    for conversation in select_ai.Conversation().list():
        print(conversation.conversation_id)
        print(conversation.attributes)


if __name__ == "__main__":
    main()

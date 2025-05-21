import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


def main():
    select_ai.connect(user=user, password=password, dsn=dsn)
    profile = select_ai.Profile()

    # matches the start of string
    for fetched_profile in profile.list(profile_name_pattern="^oci"):
        print(fetched_profile)


if __name__ == "__main__":
    main()

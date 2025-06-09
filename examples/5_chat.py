import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


def main():
    select_ai.connect(user=user, password=password, dsn=dsn)
    profile = select_ai.Profile(profile_name="oci_ai_profile")
    print(profile)
    print(profile.chat(prompt="What is OCI ?"))


if __name__ == "__main__":
    main()

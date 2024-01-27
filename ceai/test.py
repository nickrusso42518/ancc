#!/usr/bin/env python

"""
Author: Nick Russo (nickrus@cisco.com)
Purpose: Defines two factory-style functions to return
sync or async clients, and the proper user strings, for easier
consumption of Cisco Enterprise ChatGPT API service.
"""

from cisco_ai import get_client_and_user

def main():
    """
    """

    src_type = "Cisco IOS-XE"
    dst_type = "Juniper JunOS"

    with open("prompt.txt", "r", encoding="utf-8") as handle:
        prompt = handle.read()

    with open("config.txt", "r", encoding="utf-8") as handle:
        config_text = handle.read()

    question = prompt.format(src_type=src_type, dst_type=dst_type, config_text=config_text)

    client, user = get_client_and_user()
    completion = client.chat.completions.create(
        model="gpt-35-turbo",
        user=user,
        messages=[
            {
                "role": "system",
                "content": "You are a senior network engineer with extensive experience in planning, implementing, and validating network migrations.",
            },
            {
                "role": "user",
                "content": question,
            },
        ],
    )

    print(f"{completion.choices[0].message.content}")

if __name__ == "__main__":
    main()

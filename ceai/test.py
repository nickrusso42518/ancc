#!/usr/bin/env python

"""
Author: Nick Russo (nickrus@cisco.com)
Purpose: Defines two factory-style functions to return
sync or async clients, and the proper user strings, for easier
consumption of Cisco Enterprise ChatGPT API service.
"""

import json
from cisco_ai import get_client_and_user


def tabulate_intf_map(src_opt, dst_opt, intf_map):

    text = ""
    for speed, src_intf in intf_map[src_opt].items():
        dst_intf = intf_map[dst_opt].get(speed, f"src_{src_intf}")
        text += f"{src_intf},{dst_intf}\n"
    return text.strip()


def main():
    """ """

    src_opt = "cisco_iosxe"
    dst_opt = "juniper_junos"

    with open("nuances.json", "r", encoding="utf-8") as handle:
        nuances = json.load(handle)


    with open("prompt.txt", "r", encoding="utf-8") as handle:
        prompt = handle.read()

    with open("config.txt", "r", encoding="utf-8") as handle:
        config_text = handle.read()

    question = prompt.format(
        src_type=nuances["pretty"][src_opt],
        dst_type=nuances["pretty"][dst_opt],
        config_text=config_text,
        intf_map=tabulate_intf_map(src_opt, dst_opt, nuances["intf"]),
        default_secret=nuances["default_secret"],
    )

    print(question)

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

    print(f"\nAnswer:\n{completion.choices[0].message.content}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python

"""
Author: Nick Russo (nickrus@cisco.com)
Purpose: Defines two factory-style functions to return
sync or async clients, and the proper user strings, for easier
consumption of Cisco Enterprise ChatGPT API service.
"""

import json
from argparse import ArgumentParser
from ai_inputs.cisco_ai import get_client_and_user


def _make_intf_map(src_plat, dst_plat):
    """
    Given source and destination subdictionaries, map interfaces between
    the configuration styles. Returns a two-column CSV with one row for
    each source interface to be mapped.
    """

    text = ""
    for speed, src_intf in src_plat["intf"].items():
        dst_intf = dst_plat["intf"].get(speed, f"src_{src_intf}")
        text += f"{src_intf},{dst_intf}\n"
    return text.strip()


def main(args):
    """
    Execution starts here.
    """

    # Open
    with open("ai_inputs/platforms.json", "r", encoding="utf-8") as handle:
        platforms = json.load(handle)

    with open("ai_inputs/prompt.txt", "r", encoding="utf-8") as handle:
        prompt = handle.read()

    with open("ai_inputs/config.txt", "r", encoding="utf-8") as handle:
        config_text = handle.read()

    # Provide context for how the AI system should behave
    context = (
        "You are a senior network engineer with extensive experience in"
        " planning, implementing, and validating network migrations."
    )

    # Render the prompt template by providing the required inputs
    question = prompt.format(
        src_type=platforms[args.src]["type"],
        dst_type=platforms[args.dst]["type"],
        config_text=config_text,
        intf_map=_make_intf_map(platforms[args.src], platforms[args.dst]),
        include="\n".join(platforms[args.dst]["include"]),
    )
    print(question)

    # Create an API client and perform the config conversion
    client, user = get_client_and_user()
    completion = client.chat.completions.create(
        model="gpt-35-turbo",
        user=user,
        messages=[
            {
                "role": "system",
                "content": context,
            },
            {
                "role": "user",
                "content": question,
            },
        ],
    )

    print(f"\nAnswer:\n{completion.choices[0].message.content}")


if __name__ == "__main__":
    supported_platforms = [
        "arista_eos",
        "cisco_iosxe",
        "cisco_iosxr",
        "cisco_nxos",
        "juniper_junos",
    ]
    parser = ArgumentParser()
    parser.add_argument(
        "--src",
        help="source/original configuration style",
        choices=supported_platforms,
        required=True,
    )
    parser.add_argument(
        "--dst",
        help="destination/target configuration style",
        choices=supported_platforms,
        required=True,
    )
    main(parser.parse_args())

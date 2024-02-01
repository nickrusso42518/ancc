#!/usr/bin/env python

"""
Author: Nick Russo (nickrus@cisco.com)
Purpose: Defines two factory-style functions to return
sync or async clients, and the proper user strings, for easier
consumption of Cisco Enterprise ChatGPT API service.
"""

import json
from ai_inputs.cisco_ai import get_client_and_user


def main():
    """
    Execution starts here.
    """

    # Define supported platforms
    supported_platforms = [
        "arista_eos",
        "cisco_iosxe",
        "cisco_iosxr",
        "cisco_nxos",
        "juniper_junos",
    ]

    # Initialize empty dict to map OS types to their example configs
    examples = {}
    for plat in supported_platforms:
        with open(f"ai_inputs/example_{plat}.txt") as handle:
            examples[plat] = handle.read()

    # Open the platform map and fine-tune prompt template
    with open("ai_inputs/platforms.json", "r", encoding="utf-8") as handle:
        platforms = json.load(handle)

    with open("ai_inputs/ft_prompt.txt", "r", encoding="utf-8") as handle:
        prompt = handle.read()

    # Render the prompt template by providing the required inputs
    context = (
        "You are a senior network engineer with extensive experience in"
        " planning, implementing, and validating network migrations."
    )

    # Initialize empty list to store JSON message dicts as strings
    jsonl_msgs = []

    # Loop over examples in nested form, ignorning self-to-self conversions
    for src_os, src_example in examples.items():
        for dst_os, dst_example in examples.items():
            if src_os == dst_os:
                continue

            # Assemble the prompt using substitution
            question = prompt.format(
                src_type=platforms[src_os]["type"],
                dst_type=platforms[dst_os]["type"],
                config_text=src_example,
                include="\n".join(platforms[dst_os]["include"]),
            )
            messages = [
                {"role": "system", "content": context},
                {"role": "user", "content": question},
                {"role": "assistant", "content": f"```\n{dst_example}\n```"}
            ]
            jsonl_msgs.append(json.dumps({"messages": messages}))

    assert len(jsonl_msgs) == len(supported_platforms) * (len(supported_platforms)-1)
    #print("\n".join(jsonl_msgs))
    with open("training_data.jsonl", "w") as handle:
        handle.write("\n".join(jsonl_msgs) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Generates/synthesizes training data for a fine-tune
model which is specifically designed for config conversion.
"""

import json
from utils import _make_intf_map


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
    in_dir = f"gai/inputs"
    for plat in supported_platforms:
        with open(f"{in_dir}/example_{plat}.txt") as handle:
            examples[plat] = handle.read()

    # Open the platform map and fine-tune prompt template
    with open(f"{in_dir}/platforms.json", "r", encoding="utf-8") as handle:
        platforms = json.load(handle)

    with open(f"{in_dir}/ft_train_prompt.txt", "r", encoding="utf-8") as handle:
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
                intf_map=_make_intf_map(platforms[src_os], platforms[dst_os]),
                include="\n".join(platforms[dst_os]["include"]),
            )
            messages = [
                {"role": "system", "content": context},
                {"role": "user", "content": question},
                {"role": "assistant", "content": f"```\n{dst_example}\n```"},
            ]
            jsonl_msgs.append(json.dumps({"messages": messages}))

    # Ensure we had the expect number of items (n * n-1) and write to file
    num_plats = len(supported_platforms)
    assert len(jsonl_msgs) == num_plats * (num_plats - 1)
    with open(f"{in_dir}/ft_trng_data.jsonl", "w") as handle:
        handle.write("\n".join(jsonl_msgs) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python

"""
Author: Nick Russo (nickrus@cisco.com)
Purpose: Defines two factory-style functions to return
sync or async clients, and the proper user strings, for easier
consumption of Cisco Enterprise ChatGPT API service.
"""

import json
import os
from argparse import ArgumentParser
from ai_inputs.cisco_ai import get_client_and_user


def _make_intf_map(src_plat, dst_plat):
    """
    Given source and destination subdictionaries, map interfaces between
    the configuration styles. Returns a two-column CSV with one row for
    each source interface to be mapped.
    """

    # Be sure to only add source interfaces if the are unique. Example:
    # NX-OS/EOS only use "ethernet", so mapping from these types is difficult.
    text = ""
    src_seen = set()
    for speed, src_intf in src_plat["intf"].items():
        if src_intf not in src_seen:
            dst_intf = dst_plat["intf"].get(speed, f"src_{src_intf}")
            text += f"{src_intf},{dst_intf}\n"
            src_seen.add(src_intf)
    return text.strip()


def main(args):
    """
    Execution starts here.
    """

    # Open the platform map, prompt template, source config, an example files
    with open("ai_inputs/platforms.json", "r", encoding="utf-8") as handle:
        platforms = json.load(handle)

    with open("ai_inputs/prompt.txt", "r", encoding="utf-8") as handle:
        prompt = handle.read()

    with open(args.src_cfg, "r", encoding="utf-8") as handle:
        config_text = handle.read()

    with open(
        f"ai_inputs/example_{args.src_os}.txt", "r", encoding="utf-8"
    ) as handle:
        src_ex = handle.read()

    with open(
        f"ai_inputs/example_{args.dst_os}.txt", "r", encoding="utf-8"
    ) as handle:
        dst_ex = handle.read()

    # Ensure the choices directory exists for OpenAI answers
    out_dir = "choices/"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # Provide context for how the AI system should behave
    context = (
        "You are a senior network engineer with extensive experience in"
        " planning, implementing, and validating network migrations."
    )

    # Render the prompt template by providing the required inputs
    question = prompt.format(
        src_type=platforms[args.src_os]["type"],
        dst_type=platforms[args.dst_os]["type"],
        src_ex=src_ex,
        dst_ex=dst_ex,
        config_text=config_text,
        intf_map=_make_intf_map(platforms[args.src_os], platforms[args.dst_os]),
        include="\n".join(platforms[args.dst_os]["include"]),
    )
    # print(question); return

    # Create an API client and perform the config conversion. Reducing top_p
    # and temperature generates more deterministic, less creative responses.
    # presence_penalty applies a flat penalty for repetition, while
    # frequency_penalty becomes stricter as repetition increases.
    client, user = get_client_and_user()
    completion = client.chat.completions.create(
        model=args.model,
        user=user,
        n=args.num_choices,
        # top_p=0.3,
        temperature=0.8,
        presence_penalty=1,
        # frequency_penalty=0.5,
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

    # Write all answers to disk in proper directory after removing whitespace
    # and code-denoting backticks, but add a final newline
    for i, choice in enumerate(completion.choices):
        with open(f"{out_dir}/choice{i}.txt", "w", encoding="utf-8") as handle:
            handle.write(choice.message.content.strip().strip("```") + "\n")


if __name__ == "__main__":
    # Define supported platforms
    supported_platforms = [
        "arista_eos",
        "cisco_iosxe",
        "cisco_iosxr",
        "cisco_nxos",
        "juniper_junos",
    ]

    # Define supported models (change 35 to 3.5 when not using azure)
    supported_models = [
        "gpt-35-turbo",
        "gpt-4",
        "gpt-4-turbo",
    ]

    # Create parser and add src/dst OS and config arguments
    parser = ArgumentParser()
    parser.add_argument(
        "--src_os",
        help="source/original platform OS",
        choices=supported_platforms,
        required=True,
    )
    parser.add_argument(
        "--src_cfg",
        help="source/original configuration file",
        required=True,
    )
    parser.add_argument(
        "--dst_os",
        help="destination/target platform OS",
        choices=supported_platforms,
        required=True,
    )
    parser.add_argument(
        "--model",
        help="OpenAI LLM to use",
        choices=supported_models,
    )
    parser.add_argument(
        "--num_choices",
        help="number of choices to generate (iterations)",
        type=int,
        default=1,
    )

    # Alternative method to handle defaults; re-assign with desired value
    args = parser.parse_args()
    if not args.model:
        args.model = supported_models[0]

    # Call main() and pass in parsed arg object to access values
    main(args)

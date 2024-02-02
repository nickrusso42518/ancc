#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Defines two factory-style functions to return
sync or async clients, and the proper user strings, for easier
consumption of Cisco Enterprise ChatGPT API service.
"""

import json
import os
from argparse import ArgumentParser
from openai import OpenAI


def main(args):
    """
    Execution starts here.
    """

    # Open the platform map, finetune prompt template, and source config
    in_dir = "gai/inputs"
    with open(f"{in_dir}/platforms.json", "r") as handle:
        platforms = json.load(handle)

    with open(f"{in_dir}/prompt_finetune.txt", "r") as handle:
        prompt = handle.read()

    with open(args.src_cfg, "r") as handle:
        config_text = handle.read()

    # Ensure the choices directory exists to store OpenAI answers
    out_dir = "gai/choices"
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
        config_text=config_text,
        include="\n".join(platforms[args.dst_os]["include"]),
    )
    # print(question); return

    # Create an API client and perform the config conversion. Reducing top_p
    # and temperature generates more deterministic, less creative responses.
    # presence_penalty applies a flat penalty for repetition, while
    # frequency_penalty becomes stricter as repetition increases.
    client = OpenAI()
    completion = client.chat.completions.create(
        model=args.ft_model,
        n=args.num_choices,
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
    # and code-denoting backticks, but add a final newline. Use the model name
    # to differentiate between outputs between different models
    for i, choice in enumerate(completion.choices):
        with open(f"{out_dir}/{args.ft_model}_{i}.txt", "w") as handle:
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
        "--ft_model",
        help="Fine-tune LLM to use",
        required=True,
    )
    parser.add_argument(
        "--num_choices",
        help="number of choices to generate (iterations)",
        type=int,
        default=1,
    )

    # Call main() and pass in parsed arg object to access values
    main(parser.parse_args())

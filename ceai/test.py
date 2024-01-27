#!/usr/bin/env python

"""
Author: Nick Russo (nickrus@cisco.com)
Purpose: Defines two factory-style functions to return
sync or async clients, and the proper user strings, for easier
consumption of Cisco Enterprise ChatGPT API service.
"""

import json
from cisco_ai import get_client_and_user

def intf_map():
    src_type = "cisco_iosxe"
    dst_type = "juniper_junos"
    with open("intf_names/big.json", "r", encoding="utf-8") as handle:
        val_map = json.load(handle)

    src_name = val_map["pretty"][src_type]
    dst_name = val_map["pretty"][dst_type]

    text = f"{src_name},{dst_name}"
    for speed, src_intf in val_map["intf"][src_type].items():
        dst_intf = val_map["intf"][dst_type].get(speed, f"src_{src_intf}")
        text += f"\n{src_intf},{dst_intf}"
    return text
    
    

def main():
    """
    """

    src_type = "Cisco IOS-XE"
    dst_type = "Juniper JunOS"

    with open("prompt.txt", "r", encoding="utf-8") as handle:
        prompt = handle.read()

    with open("config.txt", "r", encoding="utf-8") as handle:
        config_text = handle.read()

    question = prompt.format(src_type=src_type, dst_type=dst_type, config_text=config_text, intf_map=intf_map())
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

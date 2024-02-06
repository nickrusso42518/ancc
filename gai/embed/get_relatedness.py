#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Get embeddings for Cisco and Juniper OSPF commands
and find relevance/similarities.
"""

import pandas as pd
import ast
from scipy import spatial


def _get_relatedness(e1, e2):
    """
    Measure relatedness using cosine distance, which is recommended by
    OpenAI when using their embeddings. Subtract it from 1 so that
    numbers closer to 1 represent "more" related ("less" distance).
    """
    return 1 - spatial.distance.cosine(e1, e2)


def main():
    """
    Execution starts here.
    """

    src_os = "ios"
    dst_os = "junos"

    emb = {}
    cmd_map = {}
    converters = {"embedding": ast.literal_eval}
    for plat in [src_os, dst_os]:
        emb[plat] = pd.read_csv(f"csv/{plat}.csv", converters=converters)

    for src_cmd, src_emb in zip(emb[src_os].text, emb[src_os].embedding):
        for dst_cmd, dst_emb in zip(emb[dst_os].text, emb[dst_os].embedding):
            rel_val = _get_relatedness(src_emb, dst_emb)
            if not src_cmd in cmd_map or rel_val > cmd_map[src_cmd]["rel_val"]:
                cmd_map[src_cmd] = {"dst_cmd": dst_cmd, "rel_val": rel_val}

    #import json; print(json.dumps(cmd_map, indent=2))

    t = "\n".join([f"{k},{v['dst_cmd']}"for k, v in cmd_map.items()])
    print(f"{src_os},{dst_os}\n{t}")


if __name__ == "__main__":
    main()

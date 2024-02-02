#!/usr/bin/env python

"""
Author: Nick Russo
Purpose:
"""

import json


def main():
    with open("topology.json", "r", encoding="utf-8") as handle:
        json_data = json.load(handle)

    seen = set()
    dupes = []
    for intf in map(lambda d: frozenset(d["Interface"].items()), json_data):
        if not intf in seen:
            seen.add(intf)
        else:
            dupes.append(intf)

    remaining_hosts = {dict(dupe)["hostname"] for dupe in dupes}
    sw_intf = 0
    for link in json_data:
        if frozenset(link["Interface"].items()) in dupes:
            if link["Interface"]["hostname"] in remaining_hosts:
                link["Remote_Interface"]["hostname"] = "SW"
                link["Remote_Interface"]["interface"] = sw_intf
                remaining_hosts.remove(link["Interface"]["hostname"])
                sw_intf += 1
            else:
                link["remove"] = True
                print(link)

    clean = [link for link in json_data if not link.get("remove")]
    print(json.dumps(clean, indent=2))


if __name__ == "__main__":
    main()

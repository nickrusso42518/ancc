#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Tests Batfish on sample Cisco Live sessions focused
on the OSPF routing protocol using archived configurations.
"""

import sys
import json
import pandas
from pybatfish.client.session import Session

# Global pandas formatting for string display
pandas.set_option("display.width", 1000)
pandas.set_option("display.max_columns", 20)
pandas.set_option("display.max_rows", 1000)
pandas.set_option("display.max_colwidth", None)

def main(directory):
    """
    Tests Batfish logic on a specific snapshot directory.
    """

    # Perform basic initialization per documentation
    bf = Session(host="localhost")
    bf.set_network(directory)
    bf.init_snapshot(f"snapshots/{directory}", name=directory, overwrite=True)

    # Identify the questions to ask (not calling methods yet)
    questions = {
        # "proc": bfq.ospfProcessConfiguration,
        # "intf": bfq.ospfInterfaceConfiguration,
        # "area": bfq.ospfAreaConfiguration,
        "l3if": bf.q.layer3Edges,
        "scmp": bf.q.ospfSessionCompatibility,
        "nbrs": bf.q.ospfEdges,
        "rtes": bf.q.routes,
    }

    # Unpack dictionary tuples and iterate over them
    for short_name, question in questions.items():

        # Ask the question and store the response pandas frame
        pandas_frame = question().answer().frame()
        print(f"---{short_name}---\n{pandas_frame}\n")

        # Assemble the generic file name prefix
        file_name = f"outputs/{short_name}_{directory}"

        # Generate JSON data for programmatic consumption
        json_data = json.loads(pandas_frame.to_json(orient="records"))
        with open(f"{file_name}.json", "w") as handle:
            json.dump(json_data, handle, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        main("subtopo")

    # Snapshot directory was specified; pass it into main
    else:
        main(sys.argv[1])

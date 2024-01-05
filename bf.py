#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Tests Batfish on sample Cisco Live sessions focused
on the OSPF routing protocol using archived configurations.
"""

import sys
import json
import pandas
from pybatfish.client.commands import *
from pybatfish.question import bfq, load_questions

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
    bf_session.host = "localhost"
    bf_set_network(directory)
    bf_init_snapshot(f"snapshots/{directory}", name=directory, overwrite=True)
    load_questions()

    # Identify the questions to ask (not calling methods yet)
    bf_questions = {
        "proc": bfq.ospfProcessConfiguration,
        "intf": bfq.ospfInterfaceConfiguration,
        "area": bfq.ospfAreaConfiguration,
        "nbrs": bfq.ospfEdges,
    }

    # Unpack dictionary tuples and iterate over them
    for short_name, bf_question in bf_questions.items():

        # Ask the question and store the response pandas frame
        pandas_frame = bf_question().answer().frame()

        # Assemble the generic file name prefix
        file_name = f"outputs/{short_name}_{directory}"

        # Generate JSON data for programmatic consumption
        json_data = json.loads(pandas_frame.to_json(orient="records"))
        with open(f"{file_name}.json", "w") as handle:
            json.dump(json_data, handle, indent=2)

        # Generate HTML data for web browser viewing
        html_data = pandas_frame.to_html()
        with open(f"{file_name}.html", "w") as handle:
            handle.write(html_data)

        # Generate CSV data using pipe separator (bf data has commas)
        csv_data = pandas_frame.to_csv(sep="|")
        with open(f"{file_name}.csv", "w") as handle:
            handle.write(csv_data)

        # Store string version of pandas data frame (table-like)
        with open(f"{file_name}.pandas.txt", "w") as handle:
            handle.write(str(pandas_frame))

if __name__ == "__main__":
    # Check for at least 2 CLI args; fail if absent
    if len(sys.argv) < 2:
        print("usage: python bf.py <snapshot_dir_name>")
        sys.exit(1)

    # Snapshot directory was specified; pass it into main
    else:
        main(sys.argv[1])

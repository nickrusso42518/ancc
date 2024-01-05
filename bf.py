#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Tests Batfish on sample Cisco Live sessions focused
on the OSPF routing protocol using archived configurations.
"""

import sys
import json
import logging
import pandas
from pybatfish.client import asserts
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
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("pybatfish").setLevel(logging.INFO)

    # Perform basic assertions before asking targeted questions
    asserts.assert_no_duplicate_router_ids(session=bf)
    asserts.assert_no_incompatible_ospf_sessions(session=bf)
    asserts.assert_no_forwarding_loops(session=bf)

    logging.warning("Collecting routes")
    routes = bf.q.routes().answer().frame()
    # print(routes.to_dict(orient="records"))

    # All sessions are eligible, but let's ensure neighbors form by testing
    # the number of eligible/formed edges against our expected value
    logging.warning("Comparing compatible/formed edges vs. expected: %s", "6")
    compat = bf.q.ospfSessionCompatibility().answer().frame()
    nbrs = bf.q.ospfEdges().answer().frame()
    assert len(compat) == len(nbrs) == 6

    # Ensure backbone/NSSA nodes have the external routes
    for node in ["r2", "r14"]:
        logging.warning("Checking backbone/NSSA nodes for external routes: %s", node)
        oe2 = routes.loc[(routes["Protocol"] == "ospfE2") & (routes["Node"] == node)]
        assert len(oe2) > 0

    # Ensure stub area non-ABRs do not have external routes, but have a default route
    for node in ["r13"]:
        logging.warning("Checking stub nodes for lack of external routes: %s", node)
        oe2 = routes.loc[(routes["Protocol"] == "ospfE2") & (routes["Node"] == node)]
        assert len(oe2) == 0

        logging.warning("Checking stub nodes for default IA routes: %s", node)
        defrte = routes.loc[
            (routes["Protocol"] == "ospfIA")
            & (routes["Network"] == "0.0.0.0/0")
            & (routes["Node"] == node)
        ]
        assert len(defrte) > 0

    # display(bf, directory)


def display(bf, directory):
    # Identify the questions to ask (not calling methods yet)
    questions = {
        "proc": bf.q.ospfProcessConfiguration,
        "intf": bf.q.ospfInterfaceConfiguration,
        "area": bf.q.ospfAreaConfiguration,
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

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
pandas.set_option("display.max_columns", 30)
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

    # All sessions are eligible, but let's ensure neighbors form by testing
    # the number of eligible/formed edges against our expected value
    compat = bf.q.ospfSessionCompatibility().answer().frame()
    nbrs = bf.q.ospfEdges().answer().frame()
    # print(compat); print(nbrs); breakpoint()
    logging.warning("Compare compatible vs formed edge counts: %s", len(nbrs))
    assert len(compat) == len(nbrs)

    # Check cost symmetry (ie, all link participants use same value)
    intfs = bf.q.ospfInterfaceConfiguration().answer().frame()
    # print(intfs); breakpoint()
    for _, row in nbrs.iterrows():
        li, ri = row["Interface"], row["Remote_Interface"]
        lc = intfs.loc[intfs["Interface"] == li, "OSPF_Cost"].values[0]
        rc = intfs.loc[intfs["Interface"] == ri, "OSPF_Cost"].values[0]
        logging.warning("Check symmetric cost: %s(%s)---%s(%s)", li, lc, ri, rc)
        assert lc == rc

    # Check P2P description complements (ie, routers identify one another)
    # TODO
    iprops = bf.q.interfaceProperties().answer().frame()

    logging.warning("Collect routes")
    routes = bf.q.routes().answer().frame()
    # print(routes.to_dict(orient="records"))
    # print(routes)
    # print(bf.q.ospfAreaConfiguration().answer().frame())

    # Ensure backbone/NSSA nodes have the external routes
    for node in ["r01", "r02", "r14"]:
        logging.warning("Check backbone/NSSA nodes for external routes: %s", node)
        oe2 = routes.loc[(routes["Protocol"] == "ospfE2") & (routes["Node"] == node)]
        assert len(oe2) > 0

    # Ensure stub area non-ABRs do not have external routes, but have a default route.
    # R01 is preferred for external traffic, but R14 is preferred for internal traffic.
    other_set = set()
    for node in ["r12", "r13"]:
        logging.warning("Check stub nodes for lack of external routes: %s", node)
        oe2 = routes.loc[(routes["Protocol"] == "ospfE2") & (routes["Node"] == node)]
        assert len(oe2) == 0

        logging.warning("Check stub nodes for default IA route via R01: %s", node)
        defrte = routes.loc[
            (routes["Protocol"] == "ospfIA")
            & (routes["Network"] == "0.0.0.0/0")
            & (routes["Node"] == node),
            "Next_Hop_IP",
        ]
        assert len(defrte) == 1
        assert defrte.values[0].startswith("10.1.")
        assert defrte.values[0].endswith(".1")

        logging.warning("Check stub nodes for other IA routes IA via R14: %s", node)
        others = routes.loc[
            (routes["Protocol"] == "ospfIA")
            & (routes["Network"] != "0.0.0.0/0")
            & (routes["Node"] == node),
            "Next_Hop_IP",
        ]
        assert len(others) > 1
        other_set.add(len(others))
        for other in others:
            assert other.startswith("10.")
            assert other.endswith(".14.14")

    logging.warning("Ensure stub nodes all saw %s routes", other_set)
    assert len(other_set) == 1

    # TODO reachability from stub to NSSA extranet

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
        main("pre")

    # Snapshot directory was specified; pass it into main
    else:
        main(sys.argv[1])

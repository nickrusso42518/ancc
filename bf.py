#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Tests Batfish on sample Cisco Live sessions focused
on the OSPF routing protocol using archived configurations.
"""

import sys
import logging
import pandas
from pybatfish.client import asserts
from pybatfish.client.session import Session
from pybatfish.datamodel.flow import HeaderConstraints, RoutingStepDetail

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
    logging.warning("Compare compatible vs formed edge counts: %s", len(nbrs))
    assert len(compat) == len(nbrs)

    # Check cost symmetry (ie, all link participants use same value)
    intfs = bf.q.ospfInterfaceConfiguration().answer().frame()
    for _, nbr in nbrs.iterrows():
        li, ri = nbr["Interface"], nbr["Remote_Interface"]
        lc = intfs.loc[intfs["Interface"] == li, "OSPF_Cost"].values[0]
        rc = intfs.loc[intfs["Interface"] == ri, "OSPF_Cost"].values[0]
        logging.warning("Check symmetric cost: %s(%s)---%s(%s)", li, lc, ri, rc)
        assert lc == rc

    # Check P2P description complements (ie, routers identify one another)
    iprops = bf.q.interfaceProperties().answer().frame()
    p2ps = intfs.loc[intfs["OSPF_Network_Type"] == "POINT_TO_POINT", "Interface"]

    # Loop over P2P interface ... a Series, not a DataFrame, so no iterrows()
    for p2p in p2ps:
        desc = iprops.loc[iprops["Interface"] == p2p, "Description"].values[0]
        nbr = nbrs.loc[nbrs["Interface"] == p2p, "Remote_Interface"].values[0]
        logging.warning(
            "Check complementary desc: %s / %s,%s", desc, nbr.hostname, nbr.interface
        )
        assert desc.lower().endswith(nbr.hostname)

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

    # Run unidirectional traceroute from stub to NSSA intranet (via R14)
    r10lb0 = HeaderConstraints(dstIps="r10[Loopback0]")
    for node in ["r12", "r13"]:
        tracert = (
            bf.q.traceroute(startLocation=f"{node}[Loopback0]", headers=r10lb0)
            .answer()
            .frame()
        )
        logging.warning("Traceroute: %s", str(tracert.Flow.values[0]))
        assert tracert.Traces[0][0].disposition == "ACCEPTED"

        for tstep in tracert.Traces[0][0][0].steps:
            if isinstance(tstep.detail, RoutingStepDetail):
                logging.warning("Routing step: %s", str(tstep))
                route = tstep.detail.routes[0]
                assert route.network != "0.0.0.0/0"
                assert route.nextHop.ip.startswith("10.")
                assert route.nextHop.ip.endswith(".14.14")
                break

    # Run unidirectional traceroute from stub to NSSA extranet (via R01)
    r10lb1 = HeaderConstraints(dstIps="r10[Loopback1]")
    for node in ["r12", "r13"]:
        tracert = (
            bf.q.traceroute(startLocation=f"{node}[Loopback0]", headers=r10lb1)
            .answer()
            .frame()
        )
        logging.warning("Traceroute: %s", str(tracert.Flow.values[0]))
        assert tracert.Traces[0][0].disposition == "ACCEPTED"

        for tstep in tracert.Traces[0][0][0].steps:
            if isinstance(tstep.detail, RoutingStepDetail):
                logging.warning("Routing step: %s", str(tstep))
                route = tstep.detail.routes[0]
                assert route.network == "0.0.0.0/0"
                assert route.nextHop.ip.startswith("10.1.")
                assert route.nextHop.ip.endswith(".1")
                break

    # Run undirectional traceroute from NSSA to R12 (ECMP E01/R14)
    # TODO

    # display(bf, directory)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        main("pre")

    # Snapshot directory was specified; pass it into main
    else:
        main(sys.argv[1])

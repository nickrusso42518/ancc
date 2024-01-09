#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Tests Batfish on sample Cisco Live sessions focused
on the OSPF routing protocol using archived configurations.
"""

import json
import pytest
from pybatfish.client import asserts
from pybatfish.client.session import Session
from pybatfish.datamodel.flow import HeaderConstraints, RoutingStepDetail


@pytest.fixture(scope="module")
def bf():
    """
    Perform basic initialization per documentation and return "bf" object
    so tests can interface with batfish.
    """
    bf = Session(host="localhost")
    bf.set_network("pre")
    bf.init_snapshot("snapshots/pre", name="pre", overwrite=True)
    return bf


@pytest.fixture(scope="module")
def nbrs(bf):
    """
    Return the batfish-discovered OSPF neighbors.
    """
    return bf.q.ospfEdges().answer().frame()


@pytest.fixture(scope="module")
def intfs(bf):
    """
    Return the batfish-discovered OSPF interfaces.
    """
    return bf.q.ospfInterfaceConfiguration().answer().frame()


@pytest.fixture(scope="module")
def rtes(bf):
    """
    Return the batfish-discovered IP routes.
    """
    return bf.q.routes().answer().frame()


def test_no_duplicate_router_ids(bf):
    """
    Use the built-in batfish function to ensure OSPF RIDs are unique.
    """
    asserts.assert_no_duplicate_router_ids(session=bf)


def test_no_incompatible_ospf_sessions(bf):
    """
    Use the built-in batfish function to ensure OSPF neighbors are compatible.
    """
    asserts.assert_no_incompatible_ospf_sessions(session=bf)


def test_no_forwarding_loops(bf):
    """
    Use the built-in batfish function to ensure there are no L3 loops.
    """
    asserts.assert_no_forwarding_loops(session=bf)


def test_compatible_neighbors_up(bf):
    """
    Ensure the number of compatible and established neighbors are the same.
    This is more of a sanity check and will seldom fail.
    """
    compat = bf.q.ospfSessionCompatibility().answer().frame()
    nbrs = bf.q.ospfEdges().answer().frame()
    assert len(compat) == len(nbrs)


def test_symmetric_costs(bf, intfs):
    """
    Since the target network uses equal costs on all ends of a link/segment,
    ensure that those costs are the same. This prevents asymmetric routing.
    """
    nbrs = bf.q.ospfEdges().answer().frame()
    for _, nbr in nbrs.iterrows():
        li, ri = nbr["Interface"], nbr["Remote_Interface"]
        lc = intfs.loc[intfs["Interface"] == li, "OSPF_Cost"].values[0]
        rc = intfs.loc[intfs["Interface"] == ri, "OSPF_Cost"].values[0]
        assert lc == rc


def test_complementary_descriptions(bf, nbrs, intfs):
    """
    Routers on P2P links should have descriptions ending with the peer's
    hostname, such as "TO R01" from the perspective of R12/R13.
    """
    iprops = bf.q.interfaceProperties().answer().frame()
    p2ps = intfs.loc[
        intfs["OSPF_Network_Type"] == "POINT_TO_POINT", "Interface"
    ]

    # Loop over P2P interface ... a Series, not a DataFrame, so no iterrows()
    for p2p in p2ps:
        desc = iprops.loc[iprops["Interface"] == p2p, "Description"].values[0]
        nbr = nbrs.loc[nbrs["Interface"] == p2p, "Remote_Interface"].values[0]
        assert desc.lower().endswith(nbr.hostname)


def test_nonstubs_have_externals(rtes):
    """
    Ensure backbone/NSSA nodes have the external routes redistributed by R10.
    """
    for node in ["r01", "r02", "r14"]:
        oe2 = rtes.loc[(rtes["Protocol"] == "ospfE2") & (rtes["Node"] == node)]
        assert len(oe2) > 0


def test_stubs_lack_externals(rtes):
    """
    Ensure stub nodes lack the external routes redistributed by R10.
    """
    for node in ["r12", "r13"]:
        oe2 = rtes.loc[(rtes["Protocol"] == "ospfE2") & (rtes["Node"] == node)]
        assert len(oe2) == 0


def test_stubs_have_default(rtes):
    """
    Ensure stub nodes have exactly one default route via R01.
    """
    for node in ["r12", "r13"]:
        defrte = rtes.loc[
            (rtes["Protocol"] == "ospfIA")
            & (rtes["Network"] == "0.0.0.0/0")
            & (rtes["Node"] == node),
            "Next_Hop_IP",
        ]
        assert len(defrte) == 1
        assert defrte.values[0].startswith("10.1.")
        assert defrte.values[0].endswith(".1")


def test_stubs_have_interareas(rtes):
    """
    Ensure stub nodes have at least one non-default inter-area route
    via R14. Also, these nodes must have an equal number of such routes.
    """
    other_set = set()
    for node in ["r12", "r13"]:
        others = rtes.loc[
            (rtes["Protocol"] == "ospfIA")
            & (rtes["Network"] != "0.0.0.0/0")
            & (rtes["Node"] == node),
            "Next_Hop_IP",
        ]
        assert len(others) > 0
        other_set.add(len(others))
        for other in others:
            assert other.startswith("10.")
            assert other.endswith(".14.14")

    # Ensure stub nodes all saw same number of routes
    assert len(other_set) == 1


def test_traceroute_stub_to_nssa_interarea(bf):
    """
    Run unidirectional traceroute from stub nodes to an NSSA inter-area
    destination, which must follow longer matches via R14.
    """
    for node in ["r12", "r13"]:
        params = {
            "src": f"{node}[Loopback0]",
            "dest": "r10[Loopback0]",
        }
        tracert = _run_traceroute(bf, params)

        for tstep in tracert.Traces[0][0][0].steps:
            if isinstance(tstep.detail, RoutingStepDetail):
                route = tstep.detail.routes[0]
                assert route.network != "0.0.0.0/0"
                assert route.nextHop.ip.startswith("10.")
                assert route.nextHop.ip.endswith(".14.14")
                break


def test_traceroute_stub_to_nssa_external(bf):
    """
    Run unidirectional traceroute from stub nodes to an NSSA external
    destination, which must follow the default route via R01.
    """
    for node in ["r12", "r13"]:
        params = {
            "src": f"{node}[Loopback0]",
            "dest": "r10[Loopback1]",
        }
        tracert = _run_traceroute(bf, params)

        for tstep in tracert.Traces[0][0][0].steps:
            if isinstance(tstep.detail, RoutingStepDetail):
                route = tstep.detail.routes[0]
                assert route.network == "0.0.0.0/0"
                assert route.nextHop.ip.startswith("10.1.")
                assert route.nextHop.ip.endswith(".1")
                break


def _run_traceroute(bf, params):
    """
    Helper function to run a undirectional traceroute based on the params
    dict, including "src" and "dest" targets formatted as "node[intf]".
    Ensures ACCEPTED disposition and returns traceroute dataframe.
    """
    headers = HeaderConstraints(dstIps=params["dest"])
    tracert = (
        bf.q.traceroute(startLocation=params["src"], headers=headers)
        .answer()
        .frame()
    )
    assert tracert.Traces[0][0].disposition == "ACCEPTED"
    return tracert

def test_generate_topology(bf):
    """
    Collects the layer-3 interfaces and writes them to disk in JSON format.
    This can be consumed by the lab simulation topology builder script.
    """
    links = bf.q.layer3Edges().answer().frame()
    json_data = json.loads(links.to_json(orient="records"))
    with open("topology.json", "w", encoding="utf-8") as handle:
        json.dump(json_data, handle, indent=2)

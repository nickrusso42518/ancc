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


@pytest.fixture(scope="module")
def cle(bf):
    """
    Returns a string:bool mapping to determine whether a node can
    learn OSPF external routes or not. Routers that cannot are non-ABRs
    existing only within stub/NSSA areas.
    """

    # Process tells us area assignments and ABR status
    # Area tells us area types (STUB, NSSA, NONE)
    procs = bf.q.ospfProcessConfiguration().answer().frame()
    areas = bf.q.ospfAreaConfiguration().answer().frame()

    # Map node name to true (has externals) or false (lacks externals)
    node_dict = {}
    for _, proc in procs.iterrows():
        # If node is an ABR, it can definitely learn external routes
        if proc["Area_Border_Router"]:
            node_dict[proc["Node"]] = True
            continue

        # Node is not an ABR. Need to examine individual area assignments,
        # assume can-learn-externals (cle) is False to begin
        cle = False
        for check in proc["Areas"]:
            for _, area in areas.iterrows():
                # If we found the matching node/area pair, check the area type.
                # If a non-ABR exists only in stub areas, it cannot learn
                # externals, but we must check *all* areas to be certain
                if proc["Node"] == area["Node"] and check == area["Area"]:
                    node_dict[proc["Node"]] = cle or area["Area_Type"] != "STUB"

    # Sanity check; ensure node counts are equal between data structures
    assert len(node_dict) == len(procs)
    return node_dict


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


def test_stubs_lack_externals(rtes, cle):
    """
    Ensure stub nodes lack the external routes redistributed by R10.
    """
    for node in [k for k, v in cle.items() if not v]:
        oe2 = rtes.loc[(rtes["Protocol"] == "ospfE2") & (rtes["Node"] == node)]
        assert len(oe2) == 0


def test_stubs_have_default(rtes, cle):
    """
    Ensure stub nodes have exactly one default route via R01.
    """
    for node in [k for k, v in cle.items() if not v]:
        defrte = rtes.loc[
            (rtes["Protocol"] == "ospfIA")
            & (rtes["Network"] == "0.0.0.0/0")
            & (rtes["Node"] == node),
            "Next_Hop_IP",
        ]
        assert len(defrte) == 1
        assert defrte.values[0].startswith("10.1.")
        assert defrte.values[0].endswith(".1")


def test_stubs_have_interareas(rtes, cle):
    """
    Ensure stub nodes have at least one non-default inter-area route
    via R14. Also, these nodes must have an equal number of such routes.
    """
    other_set = set()
    for node in [k for k, v in cle.items() if not v]:
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


def test_nonstubs_have_externals(rtes, cle):
    """
    Ensure backbone/NSSA nodes have the external routes redistributed by R10.
    Note that the ASBR itself will not have these external routes, but should
    have corresponding connected routes instead.
    """

    # Gather all OE2 routes in the network
    all_oe2 = rtes.loc[(rtes["Protocol"] == "ospfE2")]
    for node in [k for k, v in cle.items() if v]:
        # Get the node-specific OE2 routes and ensure more than zero exist
        oe2 = all_oe2.loc[(rtes["Node"] == node)]
        try:
            assert len(oe2) > 0

        except AssertionError:
            # This code runs for the ASBRs. Check the node's connected routes, then
            # for each unique OE2 route (using a set), ensure there is
            # exactly one corresponding connected route
            conn = rtes.loc[
                (rtes["Protocol"] == "connected") & (rtes["Node"] == node)
            ]
            for unique_oe2 in set(all_oe2.Network.values):
                assert len(conn.loc[conn["Network"] == unique_oe2]) == 1


def test_traceroute_stub_to_nssa_interarea(bf, cle):
    """
    Run unidirectional traceroute from stub nodes to an NSSA inter-area
    destination, which must follow longer matches via R14.
    """
    for node in [k for k, v in cle.items() if not v]:
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


def test_traceroute_stub_to_nssa_external(bf, cle):
    """
    Run unidirectional traceroute from stub nodes to an NSSA external
    destination, which must follow the default route via R01.
    """
    for node in [k for k, v in cle.items() if not v]:
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
    It also reforms the topology to dynamically discover multi-access networks
    so that GNS3 can add an "etherswitch" to the topology.
    This can be consumed by the lab simulation topology builder script.
    """

    # Get the layer-3 edges (links) and load them as JSON data
    links = bf.q.layer3Edges().answer().frame()
    json_data = json.loads(links.to_json(orient="records"))

    # For each link, ensure each interface has exactly one IP address,
    # then remove them. They are extraneous and GNS3 doesn't need them.
    for link in json_data:
        assert len(link["IPs"]) + len(link["Remote_IPs"]) == 2
        link.pop("IPs")
        link.pop("Remote_IPs")

        # To protect against Batfish dataframe schema changes, check for
        # the specific interface keys in each sub-dictionary
        for subdict in ["Interface", "Remote_Interface"]:
            assert subdict in link.keys()

            # Further ensure the presence of the attribute keys
            for attr in ["hostname", "interface"]:
                assert attr in link[subdict]

    # Find links that have a duplicate "Interface" dict, indicating a
    # multi-access network. Use an anomymous lambda function to create a
    # hashable dict of each "Interface" within the json_data list.
    seen = set()
    dupes = []
    for intf in map(lambda d: frozenset(d["Interface"].items()), json_data):
        # If we haven't seen this hostname/interface pair, it's unique
        if not intf in seen:
            seen.add(intf)

        # We've seen it before, so it's a duplicate (ie, multi-access network)
        else:
            dupes.append(intf)

    # Extract the duplication hostnames via set comprehension
    remaining_hosts = {dict(dupe)["hostname"] for dupe in dupes}

    # Increment counter for the GNS3 "etherswitch" interface numbering
    sw_intf = 0

    # Check entire topology for those duplicate interfaces
    for link in json_data:
        if frozenset(link["Interface"].items()) in dupes:
            # If we haven't processed that duplicate, overwrite the
            # remote hostname and interface accordingly, remove the host
            # from the set because it's just been processed, then increment
            # the switch interface counter in the format of "0/intf#"
            if link["Interface"]["hostname"] in remaining_hosts:
                link["Remote_Interface"]["hostname"] = "sw"
                link["Remote_Interface"]["interface"] = f"0/{sw_intf}"
                remaining_hosts.remove(link["Interface"]["hostname"])
                sw_intf += 1
                # TODO add reverse link from SW to router for symmetry

            # Host was already processed; mark duplicate element for removal
            else:
                link["remove"] = True

    # Rebuild topology list by excluding items marked as "remove"
    topology = [link for link in json_data if not link.get("remove")]

    # Write resulting topology to disk in pretty format
    with open("topology.json", "w", encoding="utf-8") as handle:
        json.dump(topology, handle, indent=2)

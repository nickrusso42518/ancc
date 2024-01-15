#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Tests Batfish on sample Cisco Live sessions focused
on the OSPF routing protocol using archived configurations.
"""

import json
import re
import httpx

# TODO junos?
OS_TATTR_MAP = {
    "CISCO_IOS": {"tmpl_name": "L3IOU"},
    #"JUNOS": {"tmpl_name": "VMX"}
}


def main(base_url, snapshot_name):
    """
    Execution starts here.
    """

    # Load the topology generated by the Batfish testing
    in_dir = f"outputs/{snapshot_name}"
    with open(f"{in_dir}/bf_topology.json", "r", encoding="utf-8") as handle:
        topology = json.load(handle)

    # Remove unidirectional links from the topology. eg: R01-R02 and
    # R02-R01 may exist, but we only need one pair for GNS3 specifically.
    # Use a set to filter out duplicate 2-tuples (immutable) after
    # converting each hostname/interface pair to "batfish" string format.
    unique_links = set()
    for link in topology["all_links"]:
        intfs = [
            f"[{intf['hostname']}]{intf['interface']}"
            for intf in link.values()
        ]
        unique_links.add(tuple(sorted(intfs)))

    # Sanity check; unique links must be half as big as the full topology
    assert len(topology["all_links"]) == len(unique_links) * 2

    with httpx.Client() as client:
        # Get compute nodes and find the GNS3 VM
        for comp in _req(client, f"{base_url}/computes"):
            if comp["name"].startswith("GNS3 VM"):
                print("GNS3 VM comp_id:", comp_id := comp["compute_id"])
                break
        else:
            raise ValueError("GNS3 VM compute not found")

        # Loop over all templates and expected OS attrs, then populate those
        # OS attrs with the template ID as they are discovered
        templates = _req(client, "{base_url}/templates")
        for tattr in OS_TATTR_MAP.values():
            for tmpl in templates:
                if tmpl["name"] == tattr["tmpl_name"]:
                    tattr["tmpl_id"] = tmpl["template_id"]
                    print(f"{tmpl['name']} tmpl_id: {tattr['tmpl_id']}")
                    break
            else:
                raise ValueError(f"{tattr['tmpl_name']} template not found")


        # Create a new project and store the UUID
        proj_id = _req(
            client=client,
            url=f"{base_url}/projects",
            method="post",
            jsonbody={"name": f"ancc_{snapshot_name}"},
        )["project_id"]

        # Iterate over the unique nodes, deploying each based on the
        # template. Certain parameters can be overridden/customized.
        # Update each node dict with the desired GNS3 template name (by OS)
        node_dict = {}
        for node, attrs in topology["nodes"].items():

            attrs |= {"tmpl_name": OS_TATTR_MAP[attr["Configuration_Format"]]}
            breakpoint()

            # Compute (x,y) coordations for node, creating horizonal rows of 4
            # Example placement whereby 1 is at (0,0):
            # 5 6 7 8
            # 1 2 3 4
            x, y = (i * 10 % 40, i // 4 * 10)

            # Generate the GNS3 POST payload to add a node from a template.
            # Not that some fields cannot be specified, such as "console" port
            node_body = {
                "name": node,
                "x": x,
                "y": y,
                "compute_id": comp_id,
            }

            # Deploy the node from the proper template, which varies by OS
            depl = _req(
                client=client,
                url=f"{base_url}/projects/{proj_id}/templates/{tmpl_id}",
                method="post",
                jsonbody=node_body,
            )

            print(
                f"Adding {node} at ({x},{y}) on port {depl['console']}"
                f"with id {depl['node_id']}"
            )
            node_dict[node] = depl

        # Now, make the API calls to create the links between node pairs
        for link in unique_links:
            # TODO how do we figure out the OS? can batfish tell us?
            # TODO same issue for etherswitch
            a_data = _parse_ios(link[0])
            b_data = _parse_ios(link[1])

            # Construct the HTTP body for the API call, specifying the
            # node ID (response from node creation), plus the adapter/port
            # number to be connected
            link_body = {
                "nodes": [
                    {
                        "node_id": node_dict[a_data["node"]]["node_id"],
                        "adapter_number": a_data["adapter"],
                        "port_number": a_data["port"],
                    },
                    {
                        "node_id": node_dict[b_data["node"]]["node_id"],
                        "adapter_number": b_data["adapter"],
                        "port_number": b_data["port"],
                    },
                ]
            }

            # Send a POST request to connect the A and B nodes
            conn = _req(
                client=client,
                url=f"{base_url}/projects/{proj_id}/links",
                method="post",
                jsonbody=node_body,
            )


def _parse_ios(intf_str):
    # TODO or, don't track OS, just make regex smarter
    regex = re.compile(
        r"^\[(?P<node>\S+)\][A-Za-z]*(?P<adapter>\d+)/(?P<port>\d+)$"
    )
    result = re.search(regex, intf_str)
    return result.groupdict()


def _req2(client, url, method="get", jsonbody=None):
    if "compute" in url:
        with open("old/mock_compute.json", "r", encoding="utf-8") as handle:
            return json.load(handle)

    if "template" in url:
        with open("old/mock_template.json", "r", encoding="utf-8") as handle:
            return json.load(handle)

def _req(client, url, method="get", jsonbody=None):
    """
    Issue an HTTP request using the supplied parameters, perform
    error checking to ensure status code is less than 400, then
    return the JSON structured data from the message body.
    """
    resp = client.request(url=url, method=method, json=jsonbody)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    # Can target GNS3 http://local:3080 or http://VM:80
    # main("http://192.168.120.128/v2", "pre")

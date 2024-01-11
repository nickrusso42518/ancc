#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Tests Batfish on sample Cisco Live sessions focused
on the OSPF routing protocol using archived configurations.
"""

import json
import re
import httpx


def main(base_url):
    """
    Execution starts here.
    """

    # Load the topology generated by the Batfish testing
    with open("topology.json", "r", encoding="utf-8") as handle:
        topology = json.load(handle)

    with httpx.Client() as client:
        # Get compute nodes and find the GNS3 VM
        for comp in _req(client, f"{base_url}/computes"):
            if comp["name"].startswith("GNS3 VM"):
                print("comp_id:", comp_id := comp["compute_id"])
                break
        else:
            raise ValueError("GNS3 VM compute not found")

        # Get node templates and find the L3IOU (or whichever you have)
        for tmpl in _req(client, "{base_url}/templates"):
            if tmpl["name"] == "L3IOU" and tmpl["category"] == "router":
                print("tmpl_id:", tmpl_id := tmpl["template_id"])
                break
        else:
            raise ValueError("L3IOU template not found")

        # Create a new project and store the UUID
        proj_id = _req(
            client=client,
            url=f"{base_url}/projects",
            method="post",
            jsonbody={"name": "ancc_pre"},
        )["project_id"]

        # Iterate over the unique nodes, deploying each based on the
        # template. Certain parameters can be overridden/customized.
        node_dict = {}
        for i, node in enumerate(["r01"]):
            x, y = (i * 10 % 40, i // 4 * 10)
            node_body = {
                "name": node,
                "x": x,
                "y": y,
                "compute_id": comp_id,
            }

            depl = _req(
                client=client,
                url=f"{base_url}/projects/{proj_id}/templates/{tmpl_id}",
                method="post",
                jsonbody=node_body,
            )

            print(
                f"Adding {node} at ({x},{y}) via {depl['console']} with id {depl['node_id']}"
            )
            node_dict[node] = depl
            """
            node_dict[node] = {
                "host": depl["console_host"],
                "type": depl["console_type"],
                "port": depl["console"],
                "id": depl["node_id"],
                "ports": depl["ports"],
            }
            """

        # Remove unidirectional links from the topology. eg: R01-R02 and
        # R02-R01 may exist, but we only need one pair for GNS3 specifically.
        # Use a set to filter out duplicate 2-tuples (immutable) after
        # converting each hostname/interface pair to "batfish" string format.
        unique_links = set()
        for link in topology:
            intfs = [
                f"[{intf['hostname']}]{intf['interface']}"
                for intf in link.values()
            ]
            unique_links.add(tuple(sorted(intfs)))

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
    # GNS3 client host, not the GN3 VM
    main("http://192.168.120.1:3080/v2")

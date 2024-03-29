#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Deploys a GNS3 topology based on the Batfish-inferred,
pytest-generated topology.
"""

import os
import json
import sys
import re
import httpx

# Map the network OS names (from Batfish) to their relevant attributes
OS_ATTR_MAP = {
    "CISCO_IOS": {
        "tmpl_name": "L3IOU-15.6.3",
        "scrapli_platform": "cisco_iosxe",
    },
    "FLAT_JUNIPER": {
        "tmpl_name": "Olive-12.1R1.9",
        "scrapli_platform": "juniper_junos",
    },
    "nonbf-gns3-ethsw": {"tmpl_name": "Ethernet switch"},
}


def main(base_url, snapshot_name):
    """
    Execution starts here.
    """

    # Load the topology generated by the Batfish testing
    in_dir = f"bf/state/{snapshot_name}"
    with open(f"{in_dir}/topology.json", "r") as handle:
        topology = json.load(handle)

    # Remove unidirectional links from the topology. eg: R01-R02 and
    # R02-R01 may exist, but we only need one pair for GNS3 specifically.
    # Use a set to filter out duplicate 2-tuples (immutable) after
    # converting each hostname/interface pair to "batfish" string format.
    unique_links = set()
    for link in topology["all_links"]:
        intfs = [
            f"[{intf['hostname']}]{intf['interface']}" for intf in link.values()
        ]
        unique_links.add(tuple(sorted(intfs)))

    # Sanity check; unique links must be half as big as the full topology
    assert len(topology["all_links"]) == len(unique_links) * 2
    # print(*[l for l in unique_links], sep="\n"); return

    with httpx.Client() as client:
        # Loop over all templates and expected OS attrs, then populate those
        # OS attrs with the template ID as they are discovered
        templates = _req(client, method="get", url=f"{base_url}/templates").json()
        for attr in OS_ATTR_MAP.values():
            for tmpl in templates:
                if tmpl["name"] == attr["tmpl_name"]:
                    attr["tmpl_id"] = tmpl["template_id"]
                    print(f"{tmpl['name']} tmpl_id: {attr['tmpl_id']}")
                    break
            else:
                raise ValueError(f"{attr['tmpl_name']} template not found")

        # Create a new project and store the project ID for reference
        proj_id = _req(
            client=client,
            method="post",
            url=f"{base_url}/projects",
            json={"name": f"psai_{snapshot_name}"},
        ).json()["project_id"]

        # Iterate over the unique nodes, deploying each based on the
        # template. Certain parameters can be overridden/customized.
        # Update each node dict with the desired GNS3 template name (by OS)
        node_ids, scrapli_params = {}, {}
        for i, (node, os_type) in enumerate(topology["nodes"].items()):
            # Compute (x,y) coordinates for node, creating horizonal rows of 4.
            # Example placement whereby 1 is at (0,0) in upper left corner:
            # 1 2 3 4
            # 5 6 7 8
            x, y = (i * 100 % 400, i // 4 * 100)

            # Generate the GNS3 POST payload to add a node from a template.
            # Not that some fields cannot be specified, such as "console" port.
            # "compute_id" is used to select the server to run the node.
            node_body = {
                "name": node,
                "x": x,
                "y": y,
                "compute_id": "local",
            }

            # Based on the config format, get the template ID
            tmpl_id = OS_ATTR_MAP[os_type]["tmpl_id"]

            # Deploy the node from the proper template, which varies by OS
            depl = _req(
                client=client,
                method="post",
                url=f"{base_url}/projects/{proj_id}/templates/{tmpl_id}",
                json=node_body,
            ).json()

            # Retain deployment response IDs to add links later
            node_ids[node] = depl["node_id"]

            # Build connectivity parameter dictionaries that are compatible
            # with Scrapli drivers (same key names) for use later.
            # The conditional ensures non-scrapli nodes (gns3-sw) are omitted.
            # The walrus operator := allows concurrent assignment and checking
            if sc_plat := OS_ATTR_MAP[os_type].get("scrapli_platform"):
                scrapli_params[node] = {}
                scrapli_params[node]["platform"] = sc_plat
                scrapli_params[node]["port"] = depl["console"]

            # Print the node's location and access information
            print(
                f"Adding {node} at ({x},{y}) on port {depl['console']}"
                f" with id {depl['node_id']}"
            )

            # Implement a different technique per device type. Today,
            # only (some) IOS devices can use the elegant file upload process
            if os_type == "CISCO_IOS":
                # Upload the startup configs from the Batfish snapshot
                cfg_dir = f"bf/snapshots/{snapshot_name}/configs"
                with open(f"{cfg_dir}/{node.upper()}.txt", "r") as handle:
                    config_text = handle.read()

                # Upload startup config; reponse has no body, ignore it
                node_config = f"nodes/{depl['node_id']}/files/startup-config.cfg"
                _req(
                    client=client,
                    method="post",
                    url=f"{base_url}/projects/{proj_id}/{node_config}",
                    data=config_text,
                )
                print(f"Uploaded startup-cfg for {os_type} node: {node}")
            else:
                print(f"No startup-cfg method for {os_type} node: {node}")

        # Now, make the API calls to create the links between node pairs
        for link in unique_links:
            a_data, b_data = _parse_intf(link[0]), _parse_intf(link[1])

            # Construct the HTTP body for the API call, specifying the
            # node ID (response from node creation), plus the adapter/port
            # number to be connected (convert to int first)
            link_body = {
                "nodes": [
                    {
                        "node_id": node_ids[a_data["node"]],
                        "adapter_number": int(a_data["adapter"]),
                        "port_number": int(a_data["port"]),
                    },
                    {
                        "node_id": node_ids[b_data["node"]],
                        "adapter_number": int(b_data["adapter"]),
                        "port_number": int(b_data["port"]),
                    },
                ]
            }

            # Send a POST request to connect the A and B nodes
            link_id = _req(
                client=client,
                method="post",
                url=f"{base_url}/projects/{proj_id}/links",
                json=link_body,
            ).json()["link_id"]

            # Print the link's interconnected members and ID
            print(
                f"Connected {a_data['node']}-{b_data['node']} with id {link_id}"
            )

        # Nodes and links done; start all nodes (no response)
        _req(
            client=client,
            method="post",
            url=f"{base_url}/projects/{proj_id}/nodes/start",
            json={},
        )

        # With the topology deployed, write the scrapli connection
        # parameters to disk so scrapli can consume them
        out_dir = "gns3/params"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        with open(f"{out_dir}/{snapshot_name}.json", "w") as handle:
            json.dump(scrapli_params, handle, indent=4)


def _parse_intf(intf_str):
    """
    Parse the data required to add a GNS3 link from a Batfish-formatted
    interface, such as "[r12]Ethernet0/3" in IOS or "[r01]em2.0" in JunOS.
    Return a dictionary containing the parsed matches. Use www.regex101.com
    for quick testing. Note that the trailing digit in JunOS is the unit
    (logical subinterface), not an actual port, but we'll oversimplify here.
    """
    regex = re.compile(
        r"^\[(?P<node>\S+)\][A-Za-z]*(?P<adapter>\d+)(?:/|\.)(?P<port>\d+)$"
    )
    return re.search(regex, intf_str).groupdict()


def _req(client, method, **kwargs):
    """
    Issue an HTTP request using the supplied parameters, perform
    error checking to ensure status code is less than 400, then
    return the JSON structured data from the message body.
    """
    resp = client.request(method=method, **kwargs)
    resp.raise_for_status()
    return resp


if __name__ == "__main__":
    # Ensure user supplied the required parameters; fail if not
    if len(sys.argv) != 3:
        print(f"usage: python {sys.argv[0]} <gns3_url> <bf_snapshot_name>")
        sys.exit(1)

    # Can target http://client:3080 or http://VM:80 by default (no auth)
    main(*sys.argv[1:])

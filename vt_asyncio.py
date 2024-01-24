#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Uses scrapli and asyncio to validate the live topology,
similar to Batfish, except using simulated devices and "show" commands.
"""

import asyncio
from scrapli import AsyncScrapli


# TODO Different coroutine per platform?
async def juniper_junos(hostname, conn_params):
    print("JUNOS")

    # Open async connection to the node and auto-close when context ends
    async with AsyncScrapli(**conn_params) as conn:
        # Get the prompt and ensure the supplied hostname matches
        prompt = await conn.get_prompt()
        # assert prompt.lower().startswith(hostname.lower())
    return prompt

async def cisco_iosxe(hostname, conn_params):
    """
    Coroutine that includes all validate steps to be conducted on a node.
    These run in parallel so that a certain type of test (eg checking
    OSPF neighbors) does not have to finish on all nodes before any
    node can continue. Returns None if there are no errors, or a list
    of string containing the faults.
    """

    data = {}
    print("IOSXE")

    # Open async connection to the node and auto-close when context ends
    async with AsyncScrapli(**conn_params) as conn:
        # Get the prompt and ensure the supplied hostname matches
        prompt = await conn.get_prompt()
        # assert prompt.lower().startswith(hostname.lower())

        """
        # Collect the OSPF neighbors/interfaces, then parse with custom template
        nbrs = await conn.send_command("show ip ospf neighbor")
        data["nbrs"] = nbrs.textfsm_parse_output("textfsm/ospf_nbrs.textfsm")

        intfs = await conn.send_command("show ip ospf interface brief")
        data["intfs"] = intfs.textfsm_parse_output("textfsm/ospf_intfs.textfsm")

        # TODO use new data to compare against batfish for correctness

        # TODO parse a MultiResponse directly?
        # Collect all router (type 1) and network (type 2) LSAs from the LSDB.
        # Use the existing NTC templates to parse rather than custom templates
        lsa12 = await conn.send_commands(
            ["show ip ospf database router", "show ip ospf database router"]
        )
        for i, lsa in enumerate(lsa12):
            data[f"lsa{i+1}"] = lsa.textfsm_parse_output()

        # TODO assert 6 LSA1, 1 LSA2 ... 6 dynamic, but 1 static (lazy)
        # what about areas? which area is the router in?
        assert len(data["lsa1"] == 6)
        assert len(data["lsa2"] == 1)
        """

    return prompt

async def main():
    """
    Execution starts here (coroutine).
    """

    # Basic parameters common to all nodes in the topology
    base_params = {
        "host": "192.168.120.128",  # GNS3 VM, not client
        "transport": "asynctelnet",
        #"auth_bypass": True,
        "auth_username": "root",
        "auth_password": "labadmin123",
        #"on_close": _close_channel,
        "on_open": _send_cli,
        "comms_return_char": "\r\n",  # Need for "Press RETURN to get started."
    }

    # Dynamically build from batfish (hostnames/platforms) and GNS3 (ports)
    device_map = {
        "r01": {
            "platform": "cisco_iosxe",
            "port": 5000,
        },
        "r14": {
            "platform": "juniper_junos",
            "port": 5001,
        },
    }

    tasks = [
        globals()[params["platform"]](device, base_params | params)
        for device, params in device_map.items()
    ]

    # Encapsulate all tasks in a future, then await concurrent completion
    task_future = asyncio.gather(*tasks)
    await task_future

    # TODO delete
    for result in task_future.result():
        print(result)

async def _send_cli(conn):
    """
    Close the channel but don't send "exit"; behavior appears inconsistent
    on GNS3 terminal server.
    """
    await conn.send_command("\r\n")
    return conn.send_command("cli")

async def _close_channel(conn):
    """
    Close the channel but don't send "exit"; behavior appears inconsistent
    on GNS3 terminal server.
    """
    return conn.channel.transport.close()


if __name__ == "__main__":
    asyncio.run(main())

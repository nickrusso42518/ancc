import asyncio
from scrapli import AsyncScrapli


AREA_LSA = {
    0:
        1: 4,
        2: 1,
    1:
        1: 2,
        2: 0,
    3:
        1: 4,
        2: 0,
}

# TODO Different coroutine per platform?
async def validate_node(hostname, conn_params):
    """
    Coroutine that includes all validate steps to be conducted on a node.
    These run in parallel so that a certain type of test (eg checking
    OSPF neighbors) does not have to finish on all nodes before any
    node can continue. Returns None if there are no errors, or a list
    of string containing the faults.
    """

    # TODO delete
    return f"{hostname} complete"

    data = {}

    # Open async connection to the node and auto-close when context ends
    async with AsyncScrapli(**conn_params) as conn:
        # Get the prompt and ensure the supplied hostname matches
        prompt = await conn.get_prompt()
        assert prompt.lower().startswith(hostname.lower())

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


async def main():
    """
    Execution starts here (coroutine).
    """

    # Basic parameters common to all nodes in the topology
    base_params = {
        "host": "192.168.120.128",  # GNS3 VM, not client
        "transport": "telnet",
        "auth_bypass": True,
        "on_close": _close_channel,
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
        validate_node(device, base_params | params)
        for device, params in device_map.items()
    ]

    # Encapsulate all tasks in a future, then await concurrent completion
    task_future = asyncio.gather(*tasks)
    await task_future

    # TODO delete
    for result in task_future.result():
        print(result)


def _close_channel(conn):
    """
    Close the channel but don't send "exit"; behavior appears inconsistent
    on GNS3 terminal server.
    """
    conn.channel.transport.close()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Uses scrapli and asyncio to validate the live topology,
similar to Batfish, except using simulated devices and "show" commands.
"""

import asyncio
import logging
import json
import operator
import os
import sys
from scrapli import AsyncScrapli


async def juniper_junos(hostname, snapshot_name, conn_params):
    """
    Coroutine to collect information from Juniper JunOS devices. The
    only assertions performed are procedural/technical sanity checks.
    """

    # Create a logger for this node in CSV format
    logger = setup_logger(f"gns3/logs/{hostname}_log.csv")

    # Update the dict to set custom open/close actions
    conn_params |= {"on_open": _open_junos, "on_close": _close_junos}

    # Open async connection to the node and auto-close when context ends
    async with AsyncScrapli(**conn_params) as conn:
        # Get the prompt and ensure the supplied hostname matches
        prompt = await conn.get_prompt()
        test(prompt.strip(), operator.eq, "root>", logger)

        # Load the initial config (cannot be done via GNS3 API)
        filepath = f"bf/snapshots/{snapshot_name}/configs/{hostname.upper()}.txt"
        await conn.send_configs_from_file(filepath, stop_on_failed=True)

        # TODO collect neighbors, interfaces, and LSDB
        # TODO custom textfsm for interfaces
    return prompt


async def cisco_iosxe(hostname, snapshot_name, conn_params):
    """
    Coroutine to collect information from Cisco IOS-XE devices. The
    only assertions performed are procedural/technical sanity checks.
    """

    # Create a logger for this node in CSV format
    logger = setup_logger(f"gns3/logs/{hostname}_log.csv")

    # Update the dict to set a custom close
    conn_params["on_close"] = _close_iosxe
    # TODO data = {}

    # Open async connection to the node and auto-close when context ends
    async with AsyncScrapli(**conn_params) as conn:
        # Get the prompt and ensure the supplied hostname matches
        prompt = await conn.get_prompt()
        test(prompt.lower().strip(), operator.eq, hostname + "#", logger)

        # NOT NEEDED FOR IOU, but you can perform IOS-XE initialization
        # for a specified snapshot here, if necessary. Example:
        # filepath = f"snapshots/{snapshot_name}/configs/{hostname.upper()}.txt"
        # await conn.send_configs_from_file(filepath, stop_on_failed=True)

        _ = """
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


async def main(snapshot_name):
    """
    Execution starts here (coroutine). Targets a specific Batfish
    snapshot, using those Scrapli parameters
    """

    # Ensure the logs directory exists for virtual topology test results
    out_dir = "gns3/logs"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # Basic parameters common to all nodes in the topology
    base_params = {
        "host": "192.168.120.128",  # Targetting GNS3 VM, not laptop client
        "transport": "asynctelnet",  # or "asyncssh" if desired
        "auth_bypass": True,  # don't perform telnet authentication
        "comms_return_char": "\r\n",  # Cisco "Press RETURN to get started."
    }

    # Load device/console port mappings dynamically built from GNS3
    in_dir = "gns3/params"
    device_file = f"{in_dir}/{snapshot_name}.json"
    with open(device_file, "r", encoding="utf-8") as handle:
        device_map = json.load(handle)

    # Instantiate coroutines into tasks, assemble into list for
    # all devices. Regardless of OS, they can all run together
    tasks = [
        globals()[params["platform"]](device, snapshot_name, base_params | params)
        for device, params in device_map.items()
    ]

    # Encapsulate all tasks in a future, then await concurrent completion
    task_future = asyncio.gather(*tasks)
    await task_future

    # TODO delete
    for result in task_future.result():
        print(result)


async def _open_junos(conn):
    """
    Perform initial console login and enter the CLI, then apply the standard
    terminal settings.
    """

    # TODO use sync scrapli as standalone?
    # Low-level interactions to enter the CLI
    login_interactions = [
        ("\n", "Amnesiac (ttyd0)\n\nlogin:"),
        ("root", "root@%"),
        ("cli", "root>"),
    ]

    # Standard Scrapli terminal settings; must repeat since we defined on_open
    setup_cmds = [
        "set cli screen-length 0",
        "set cli screen-width 511",
        "set cli complete-on-space off",
    ]

    # Perform the login interactions, being graceful on timeouts
    for cmd, resp in login_interactions:
        resp = await conn.send_and_read(
            channel_input=cmd,
            expected_outputs=[resp],
            read_duration=10,
            timeout_ops=10,
        )

    # Send terminal settings, don't care about result
    await conn.send_commands(setup_cmds)


async def _close_junos(conn):
    """
    First exit the CLI and wait for the FreeBSD shell, then
    close the channel normally.
    """
    for resp in ["root@%", "Amnesiac (ttyd0)\n\nlogin:"]:
        await conn.send_and_read(channel_input="exit", expected_outputs=[resp])
    conn.channel.transport.close()


async def _close_iosxe(conn):
    """
    Close the channel but don't send "exit"; behavior appears inconsistent
    on GNS3 terminal server. Just leave the console line open.
    """
    conn.channel.transport.close()


def setup_logger(log_file):
    """
    Given a log file name (path), this function returns a new logger
    object to write into the specified file. Also writes the column names
    of "time,value1,operator,value2,result" without any formatting.
    """

    handler = logging.FileHandler(log_file, mode="w")
    logger = logging.getLogger(log_file)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.info("time,value1,operator,value2,result")
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s.%(msecs)03d,%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    return logger


def test(v1, op, v2, logger=None):
    """
    Compare values v1 and v2 using the operator specified. Prints a
    message in the format "v1,op,v2,result" separated by commas for
    easy logging via the specified logger, or to to stdout if
    no logger is specified.
    """
    sym = {
        "eq": "==",
        "ne": "!=",
        "gt": ">",
        "ge": ">=",
        "lt": "<",
        "le": "<=",
        "contains": "in",
    }
    name = op.__name__
    display_method = logger.info if logger else print
    display_method(f"{v1},{sym.get(name, name)},{v2},{op(v1, v2)}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))

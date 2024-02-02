#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Uses pytest, asyncio, and scrapli to test the virtual
routers in the topology using CLI commands and assertions.
"""

import json
import pytest
from scrapli import Scrapli
import time

def _close_channel(ascrap):
    """
    Close the channel but don't send "exit"; behavior appears inconsistent
    on GNS3 terminal server.
    """
    # ascrap.channel.transport.socket.close()
    ascrap.channel.transport.close()

@pytest.fixture(scope="module")
def conn():
    """
    Fixture to provide access to the devices with
    telnet transport to the device consoles.
    """

    params = {
       "host": "192.168.120.128",  # GNS3 VM, not client
       "platform": "cisco_iosxe",
       "transport": "telnet",
       "auth_bypass": True,
       "on_close": _close_channel,
       "comms_return_char": "\r\n", # Need for "Press RETURN to get started."
       "genie_platform": "ios"
    }

    # Setup: define and open all connections
    conn = {
        "r01": Scrapli(**{"port": 5000} | params),
        "r02": Scrapli(**{"port": 5001} | params),
    }
    for ascrap in conn.values():
        ascrap.open()

    # Return the connection map to test functions
    yield conn

    # Teardown: close all connections
    for ascrap in conn.values():
        ascrap.close()

def test_prompt(conn):
    """
    Ensure the device's prompt is accessible and contains the
    case-insensitive hostname.
    """
    for hostname, ascrap in conn.items():
        assert ascrap.isalive()
        prompt = ascrap.get_prompt()
        assert hostname.lower() in prompt.lower()

def test_ospf_neighbors(conn):
    nbrs_dict = {}
    for hostname, ascrap in conn.items():
        nbrs = ascrap.send_command("show ip ospf neighbor detail")
        breakpoint()
        nbrs_d = nbrs.genie_parse_output()
        assert nbrs_d
        nbrs_dict[hostname] = nbrs_d

    assert len(conn) == len(nbrs_dict)
    with open("outputs/vt_nbrs.json", "w", encoding="utf-8") as handle:
        json.dump(nbrs_dict, handle, indent=2)

def test_ospf_interfaces(conn):
    intfs_dict = {}
    for hostname, ascrap in conn.items():
        intfs = ascrap.send_command("show ip ospf interface")
        intfs_d = intfs.genie_parse_output()
        assert intfs_d
        nbrs_dict[hostname] = intfs_d

    assert len(conn) == len(intfs_dict)
    with open("outputs/vt_intfs.json", "w", encoding="utf-8") as handle:
        json.dump(intfs_dict, handle, indent=2)

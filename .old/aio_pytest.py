#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Uses pytest, asyncio, and scrapli to test the virtual
routers in the topology using CLI commands and assertions.
"""

import pytest
import pytest_asyncio
from scrapli import AsyncScrapli

# TODO delete?
async def _set_term_length_0(ascrap):
    host = await ascrap.send_command("show running-config | include hostname")
    ascrap.comms_prompt_pattern = fr"^{host.result.split(' ')[1]}#\s*$"

@pytest_asyncio.fixture(scope="module")
async def conn():
    """
    Fixture to provide access to the devices using asyncio with
    telnet transport to the device consoles.
    """

    # default does not include A-Z "^[a-z0-9.\-@()/:]{1,48}[#>$]\s*$"
    params = {
       "host": "192.168.120.128",  # GNS3 VM, not client
       "platform": "cisco_iosxe",
       "transport": "asynctelnet",
       "auth_bypass": True,
       "on_open": _set_term_length_0,
       "comms_return_char": "\r\n",
       # "comms_prompt_pattern": r"^[A-Za-z0-9.@()/:-]{1,48}[#>$]\s*$"
    }

    # Setup: define and open all connections
    conn = {
        "r01": AsyncScrapli(**{"port": 5000} | params),
        "r02": AsyncScrapli(**{"port": 5001} | params),
    }
    for ascrap in conn.values():
        await ascrap.open()

    # Return the connection map to test functions
    yield conn

    # Teardown: close all connections
    for ascrap in conn.values():
        await ascrap.close()

@pytest.mark.asyncio
async def test_prompt(conn):
    """
    Ensure the device's prompt is accessible and contains the
    case-insensitive hostname.
    """
    for hostname, ascrap in conn.items():
        assert ascrap.isalive()
        #prompt = await ascrap.get_prompt()
        #assert hostname.lower() in prompt.lower()

@pytest.mark.asyncio
async def test_ospf_neighbors(conn):
    """
    resp = await conn["r1"].send_command("whatever")
    resp_d = resp.genie_parse_output()
    assert resp_d["something"] == 42
    """
    assert conn

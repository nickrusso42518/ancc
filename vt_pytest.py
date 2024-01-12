#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Uses pytest, asyncio, and scrapli to test the virtual
routers in the topology using CLI commands and assertions.
"""

import pytest
import pytest_asyncio
from scrapli import AsyncScrapli

@pytest_asyncio.fixture(scope="module")
async def conn():
    """
    Fixture to provide access to the devices using asyncio with
    telnet transport to the device consoles.
    """
    device = {
       "host": "freechess.org",
       "port": 23,
       "auth_strict_key": False,
       "platform": "cisco_iosxe",
       "transport": "asynctelnet",
    }

    # Setup: define and open all connections
    conn = {
        "r01": AsyncScrapli(**device),
        "r02": AsyncScrapli(**device),
    }
    for ascrap in conn.values():
        await ascrap.open()

    # Return the connection map to test functions
    yield conn

    # Teardown: close all connections
    for ascrap in conn.values():
        ascrap.close()

@pytest.mark.asyncio
async def test_prompt(conn):
    """
    Ensure the device's prompt is accessible and contains the
    case-insensitive hostname.
    """
    for hostname, ascrap in conn.items():
        prompt = await ascrap.get_prompt()
        assert hostname.lower() in prompt.lower()

@pytest.mark.asyncio
async def test_ospf_neighbors(conn):
    """
    resp = await conn["r1"].send_command("whatever")
    resp_d = resp.genie_parse_output()
    assert resp_d["something"] == 42
    """
    assert conn

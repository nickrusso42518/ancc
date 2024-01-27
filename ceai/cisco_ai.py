#!/usr/bin/env python

"""
Author: Nick Russo (nickrus@cisco.com)
Purpose: Defines two factory-style functions to return
sync or async clients, and the proper user strings, for easier
consumption of Cisco Enterprise ChatGPT API service.
"""

import os
import asyncio
import httpx
from openai import AzureOpenAI, AsyncAzureOpenAI


def _get_token_and_user(
    cisco_client_id=None, cisco_client_secret=None, openai_appkey=None
):
    """
    Common method for sync/async clients to get an access token
    and format the user string. Not suitable for direct consumption.
    """

    if not cisco_client_id:
        cisco_client_id = os.environ["CISCO_CLIENT_ID"]
    if not cisco_client_secret:
        cisco_client_secret = os.environ["CISCO_CLIENT_SECRET"]
    if not openai_appkey:
        openai_appkey = os.environ["OPENAI_APPKEY"]

    # For extra certainty, hardcode headers
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # Obtain API key (access token) using HTTP basic auth
    token_resp = httpx.post(
        url="https://id.cisco.com/oauth2/default/v1/token",
        auth=(cisco_client_id, cisco_client_secret),
        headers=headers,
        data={"grant_type": "client_credentials"},
    )
    token_resp.raise_for_status()

    # Get app key, which represents the "user" in chat completions.
    return token_resp.json()["access_token"], f'{{"appkey": "{openai_appkey}"}}'


def get_client_and_user(
    cisco_client_id=None, cisco_client_secret=None, openai_appkey=None
):
    """
    Use cisco_client_id/cisco_client_secret as basic auth parameters
    to get an OpenAI access token. If any arguments are unspecified,
    try to read env vars. These will raise KeyErrors if they are
    also unspecified. Returns an AzureOpenAI (sync) client along with
    a properly formatted "user" string to include in completion requests.
    Unpack them like so:  client, user = get_client_and_user()
    """

    # Call the common method to get an access token and user string
    token, user = _get_token_and_user(
        cisco_client_id, cisco_client_secret, openai_appkey
    )

    # Create OpenAI API client to Azure instance (sync)
    client = AzureOpenAI(
        azure_endpoint="https://chat-ai.cisco.com",
        api_key=token,
        api_version="2023-05-15",
    )

    # Return a 2-tuple of the client and user for easy unpacking
    return client, user


def get_async_client_and_user(
    cisco_client_id=None, cisco_client_secret=None, openai_appkey=None
):
    """
    Use cisco_client_id/cisco_client_secret as basic auth parameters
    to get an OpenAI access token. If any arguments are unspecified,
    try to read env vars. These will raise KeyErrors if they are
    also unspecified. Returns an AsyncAzureOpenAI client along with
    a properly formatted "user" string to include in completion requests.
    Unpack them like so:  client, user = get_async_client_and_user()
    """

    # Call the common method to get an access token and user string
    token, user = _get_token_and_user(
        cisco_client_id, cisco_client_secret, openai_appkey
    )

    # Create OpenAI API client to Azure instance (async)
    client = AsyncAzureOpenAI(
        azure_endpoint="https://chat-ai.cisco.com",
        api_key=token,
        api_version="2023-05-15",
    )

    # Return a 2-tuple of the client and user for easy unpacking
    return client, user


def _sync_test():
    """
    Internal test for the sync client. Not suitable for direct consumption.
    """
    client, user = get_client_and_user()
    sample_question = "In 4 sentences or less, tell me why it rains."

    completion = client.chat.completions.create(
        model="gpt-35-turbo",
        user=user,
        messages=[
            {
                "role": "system",
                "content": "You are a weather expert.",
            },
            {
                "role": "user",
                "content": sample_question,
            },
        ],
    )

    assert len(completion.choices) > 0
    print(f"\nSync question: {sample_question}")
    print(f"Answer: {completion.choices[0].message.content}")


async def _async_test():
    """
    Internal test for the async client. Not suitable for direct consumption.
    """
    client, user = get_async_client_and_user()
    sample_question = "In 4 sentences or less, tell me why it snows."

    completion = await client.chat.completions.create(
        model="gpt-35-turbo",
        user=user,
        messages=[
            {
                "role": "system",
                "content": "You are a weather expert.",
            },
            {
                "role": "user",
                "content": sample_question,
            },
        ],
    )

    assert len(completion.choices) > 0
    print(f"\nAsync question: {sample_question}")
    print(f"Answer: {completion.choices[0].message.content}")


if __name__ == "__main__":
    _sync_test()
    asyncio.run(_async_test())

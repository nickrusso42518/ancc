#!/usr/bin/env python

"""
Author: Nick Russo (nickrus@cisco.com)
Purpose: Defines two factory-style functions to return
sync or async clients, and the proper user strings, for easier
consumption of Cisco Enterprise ChatGPT API service.
"""

from datetime import datetime
import os
import asyncio
import httpx
from openai import AzureOpenAI, AsyncAzureOpenAI


def account_for_costs(completion):
    """
    Given a completion response object, this approximates the
    monetary cost in US dollars required to build the completion.
    Returns a comma-separated string designed for writing to a log
    file detailing the relevant tokens, rates, and costs. Format:
      datetime,prompt_tokens,prompt_rate,prompt_cost,
        completion_tokens,completion_rate,completion_cost,
        total_tokens,total_cost
    """

    # Define the token billing rates per 1000 tokens for the model.
    # Values may change. Check here: https://openai.com/pricing
    cost_map = {
        "gpt-35-turbo": {
            "prompt_rate": 0.001,
            "completion_rate": 0.002,
        },
        "gpt-4": {
            "prompt_rate": 0.03,
            "completion_rate": 0.06,
        },
        "gpt-4-turbo": {
            "prompt_rate": 0.01,
            "completion_rate": 0.03,
        },
    }

    # Simplify the model name so it has an associated dict key.
    # Let the KeyError break the process if model is unsupported.
    if completion.model.startswith("gpt-35-turbo"):
        model = "gpt-35-turbo"
    elif completion.model.startswith("gpt-4") and completion.model.endswith("preview"):
        model = "gpt-4-turbo-preview"
    elif completion.model.startswith("gpt-4"):
        model = "gpt-4"
    else:
        model = completion.model

    # Assign prompt tokens, rate, and cost values
    pt = completion.usage.prompt_tokens
    pr = cost_map[model]["prompt_rate"]
    pc = (pt / 1000) * pr

    # Assign completion tokens, rate, and cost values
    ct = completion.usage.completion_tokens
    cr = cost_map[model]["completion_rate"]
    cc = (ct / 1000) * cr

    # Assign total tokens, cost values, and date/time group
    tt = completion.usage.total_tokens
    tc = pc + cc
    dtg = datetime.fromtimestamp(completion.created)

    # Return data in CSV format to include all variables.
    # Costs are shown to 8 decimal places of precision
    return f"{dtg},{pt},{pr},{pc:.8f},{ct},{cr},{cc:.8f},{tt},{tc:.8f}"


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
    print(f"\n\nSync question: {sample_question}")
    print(f"Answer: {completion.choices[0].message.content}")
    print(f"\nCost log: {account_for_costs(completion)}")


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
    print(f"\n\nAsync question: {sample_question}")
    print(f"Answer: {completion.choices[0].message.content}")
    print(f"\nCost log: {account_for_costs(completion)}")


if __name__ == "__main__":
    _sync_test()
    asyncio.run(_async_test())

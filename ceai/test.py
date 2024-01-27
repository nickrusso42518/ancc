#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Uses OpenAI API to convert a network device configuration
between platforms.
"""

import os
import httpx
from openai import AzureOpenAI


def get_client_and_user(
    cisco_client_id=None, cisco_client_secret=None, openai_appkey=None
):
    """
    Execution starts here.
    """

    # If any arguments are unspecified, try to read env vars.
    # These will raise KeyErrors if they are also unspecified.
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
    with httpx.Client() as hxc:
        token_resp = hxc.post(
            url="https://id.cisco.com/oauth2/default/v1/token",
            auth=(cisco_client_id, cisco_client_secret),
            headers=headers,
            data={"grant_type": "client_credentials"},
        )
    token_resp.raise_for_status()

    # Create OpenAI API client to Azure instance
    client = AzureOpenAI(
        azure_endpoint="https://chat-ai.cisco.com",
        api_key=token_resp.json()["access_token"],
        api_version="2023-05-15",
    )

    # Get app key, which represents the "user" in chat completions.
    user = f'{{"appkey": "{openai_appkey}"}}'

    # Return a 2-tuple of the client and user for easy unpacking
    return client, user

def main():
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
    print(f"Question: {sample_question}")
    print(f"Answer: {completion.choices[0].message.content}")

if __name__ == "__main__":
    main()

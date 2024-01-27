#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Uses OpenAI API to convert a network device configuration
between platforms.
"""

import os
import httpx
from openai import AzureOpenAI


def main():
    """
    Execution starts here.
    """

    # Obtain API key (access token) using HTTP basic auth via the
    # client_id and client_secret values.
    token_resp = httpx.post(
        url="https://id.cisco.com/oauth2/default/v1/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        auth=tuple(os.environ[ev] for ev in ["CLIENT_ID", "CLIENT_SECRET"]),
        data={"grant_type": "client_credentials"},
    )
    token_resp.raise_for_status()

    # Get app key, which represents the "user" in chat completions.
    appkey = os.environ["OPENAI_APPKEY"]
    user = f'{{"appkey": "{appkey}"}}'

    # Create OpenAI API client to Azure instance
    client = AzureOpenAI(
        azure_endpoint='https://chat-ai.cisco.com', 
        api_key=token_resp.json()["access_token"],  
        api_version="2023-05-15"
    )

    # Start conversions via chat completion
    completion = client.chat.completions.create(
        model="gpt-35-turbo",
        user=user,
        messages=[
            {
                "role": "system",
                "content": "You are a senior network engineer with extensive experience with Cisco products.",
            },
            {
                "role": "user",
                "content": "In 4 sentences or less, summarize the difference between Cisco IOS-XE and Cisco IOS-XR",
            },
        ],
    )

    # Print all messages within each choice
    for choice in completion.choices:
        print(choice.message.content)


if __name__ == "__main__":
    main()

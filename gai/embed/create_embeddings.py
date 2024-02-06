#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Get embeddings for Cisco and Juniper OSPF commands
and find relevance/similarities.
"""

import backoff
import openai
import pandas as pd


@backoff.on_exception(backoff.expo, openai.RateLimitError)
def _create_embeddings(client, **kwargs):
    """
    Decorated function that creates embeddings while obeying
    OpenAI's rate limits using an exponential backoff algorithm.
    This could be based on request or token quantities.
    """
    return client.embeddings.create(**kwargs)


def main():
    """
    Execution starts here.
    """

    # Initialize "database", OpenAI client, and model choice
    client = openai.OpenAI()
    model = "text-embedding-3-large"

    # Process each key (platform) in the database
    for plat in ["ios", "junos"]:
        # Read in the commands from each file, converting them to
        # a set to guarantee uniqueness (and reduce cost). Strip
        # whitespace and ignore comments denoted by #
        with open(f"cmd/{plat}_dump.txt", "r") as handle:
            cmds = list({c.strip() for c in handle if not c.startswith("#")})

        # Create embeddings and ensure equal lengths between
        # input text (commands) and embedding responses
        resp = _create_embeddings(client, model=model, input=cmds)
        assert len(cmds) == len(resp.data)

        # Create pandas dataframe (table) mapping the text inputs (commands)
        # to their just-created OpenAI embeddings. Use a small, anonymous
        # lambda function to extract the "embedding" object from each data
        # element in the API response
        df = pd.DataFrame(
            {"text": cmds, "embedding": map(lambda emb: emb.embedding, resp.data)}
        )

        # Write the pandas dataframe to disk; we don't want to spend money
        # creating embeddings multiple times when we need to consume them
        df.to_csv(f"csv/{plat}.csv", index=False)


if __name__ == "__main__":
    main()

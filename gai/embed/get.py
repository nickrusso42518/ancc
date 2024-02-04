#!/usr/bin/env python

"""
Author: Nick Russo
Purpose: Get embeddings for Cisco and Juniper OSPF commands
and find relevance/similarities.
"""

import backoff
import openai

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
    db = {"ios": {}, "junos": {}}
    client = openai.OpenAI()
    model = "text-embedding-ada-002"

    # Process each key (platform) in the database
    for plat in db:

        # Read in the commands from each file, converting them to
        # a set to guarantee uniqueness (and reduce cost). Strip
        # whitespace and ignore comments denoted by #
        with open(f"{plat}_small.txt", "r") as handle:
            cmds = list({c.strip() for c in handle if not c.startswith("#")})

        # Create embeddings and ensure equal lengths between
        # input text (commands) and embedding responses
        resp = _create_embeddings(client, model=model, input=cmds)
        assert len(cmds) == len(resp.data)

        # Loop over embeddings, assigning each giant list of floats to
        # the corresponding command key. Paranoid check: ensure the
        # loop counter equals the OpenAI embedding index
        for i, (cmd, emb) in enumerate(zip(cmds, resp.data)):
            assert i == emb.index
            db[plat][cmd] = emb.embedding

    # print(db)

if __name__ == "__main__":
    main()

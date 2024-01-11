@pytest.fixture(scope="module")
def conn():
    return {
        "r1": new AsyncScrapli(**r1_params),
        "r2": new AsyncScrapli(**r2_params),
    }

@pytest.mark.asyncio
def test_1(conn):
    resp = await conn["r1"].send_command("whatever")
    resp = resp.use_genie()
    assert resp["something"] == 42

import pytest

def pytest_addoption(parser):
    parser.addoption("--snapshot_name", action="store")

@pytest.fixture(scope='session')
def snapshot_name(request):
    return request.config.option.snapshot_name

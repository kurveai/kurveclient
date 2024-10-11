from pytest import fixture
import pathlib


@fixture(scope="function")
def mock_creds():
    yield pathlib.Home() / '.kurve' / 'config.json'


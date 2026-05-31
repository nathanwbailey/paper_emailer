from unittest.mock import patch
import pytest


@pytest.fixture(autouse=True)
def no_dotenv():
    with patch("dotenv.load_dotenv", return_value=False):
        yield

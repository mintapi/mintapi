import os
import sys

import pytest
from mintapi.browser import SeleniumBrowser
from mintapi.signIn import _create_web_driver_at_mint_com, sign_in
from tests.sample_endpoint_payloads import category_example

USERNAME = os.environ.get("MINTAPI_USERNAME", None)
PASSWORD = os.environ.get("MINTAPI_PASSWORD", None)
HEADLESS = os.environ.get("MINTAPI_HEADLESS", "True") in [
    "true",
    "True",
]  # convert to boolean, defaults to true
USE_CHROMEDRIVER_ON_PATH = not os.environ.get(
    "MINTAPI_CHROMEDRIVER_ON_PATH", "False"
) in [
    "False",
    "false",
]  # convert to boolean, defaults to false
SESSION_PATH = os.environ.get("MINTAPI_SESSION", None)
MFA_METHOD = os.environ.get("MINTAPI_MFA_METHOD", None)
MFA_TOKEN = os.environ.get("MINTAPI_MFA_TOKEN", None)
INTUIT_ACCOUNT = os.environ.get("MINTAPI_INTUIT_ACCOUNT", None)
pytestmark = pytest.mark.skipif(
    USERNAME is None or PASSWORD is None, reason="This module requires sign in"
)


@pytest.fixture
def get_mint_driver() -> SeleniumBrowser:
    browser = SeleniumBrowser()
    browser.driver = _create_web_driver_at_mint_com(
        HEADLESS,
        SESSION_PATH,
        USE_CHROMEDRIVER_ON_PATH,
    )
    yield browser
    browser.close()


@pytest.fixture
def do_sign_in(get_mint_driver: SeleniumBrowser) -> SeleniumBrowser:
    sign_in(
        USERNAME,
        PASSWORD,
        get_mint_driver.driver,
        MFA_METHOD,
        MFA_TOKEN,
        INTUIT_ACCOUNT,
    )
    return get_mint_driver


def test_sign_in(get_mint_driver: SeleniumBrowser):
    sign_in(
        USERNAME,
        PASSWORD,
        get_mint_driver.driver,
        MFA_METHOD,
        MFA_TOKEN,
        INTUIT_ACCOUNT,
    )
    assert get_mint_driver.driver.current_url.startswith(
        "https://mint.intuit.com/overview"
    )


def test_investment_endpoint(do_sign_in: SeleniumBrowser):
    investment_data = do_sign_in.get_investment_data()[0]
    assert "metaData" not in investment_data
    assert "lastUpdatedDate" in investment_data


def test_get_categories(do_sign_in: SeleniumBrowser):
    categories = do_sign_in.get_categories()
    for key in category_example[0].keys():
        assert key in categories[0].keys()


if __name__ == "__main__":
    pytest.main(sys.argv)

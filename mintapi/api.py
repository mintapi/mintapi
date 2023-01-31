from typing import Dict, List, Optional, Union

from mintapi.browser import SeleniumBrowser
from mintapi.rest import RESTClient


class Mint(object):
    """
    Composed API client to route through the browser or REST calls
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cookies: Optional[Union[str, List[Dict]]] = None,
        use_rest_client: bool = False,
        **browser_params
    ):
        """
        Passes forward parameters to the browser and rest client

        Pass a driver or email + password to authenticate with the browser
        OR pass in an api_key or cookie to auth directly with the rest client
        Browser is mainly used to generate auth (only necessary if not otherwise passed)

        Backward compatibility flag defaults to not use new rest client
        (behavior subject to change in future releases)
        """
        if not use_rest_client:
            # legacy behavior
            self.browser = SeleniumBrowser(**browser_params)
            self.rest_client = None

        else:
            self.rest_client = RESTClient(api_key=api_key, cookies=cookies)

            # only use browser if not sufficiently authorized already
            if not api_key or not cookies:
                self.browser = SeleniumBrowser(**browser_params)

                if self.browser.driver is not None:
                    self.transfer_auth()
                self.browser.close()
            else:
                self.browser = None

    def transfer_auth(self):
        api_key = self.browser._get_api_key_header()["authorization"]
        cookies = self.browser._get_cookies()
        self.rest_client.authorize(cookies=cookies, api_key=api_key)

    def __getattr__(self, attr):
        """
        Automatically handle routing to prefer the rest client but fallback to the browser for unimplemented
        methods
        """
        if self.rest_client is not None and hasattr(self.rest_client, attr):
            return getattr(self.rest_client, attr)
        elif self.browser is not None and hasattr(self.browser, attr):
            return getattr(self.browser, attr)
        else:
            raise NotImplementedError


def get_accounts(email, password, **kwargs):
    mint = Mint(email=email, password=password, **kwargs)
    return mint.get_account_data()


def get_net_worth(email, password, **kwargs):
    mint = Mint(email=email, password=password, **kwargs)
    return mint.get_net_worth_data()


def get_budgets(email, password, **kwargs):
    mint = Mint(email=email, password=password, **kwargs)
    return mint.get_budget_data()


def get_credit_score(email, password, **kwargs):
    mint = Mint(email=email, password=password, **kwargs)
    return mint.get_credit_score()


def get_credit_report(email, password, **kwargs):
    mint = Mint(email=email, password=password, **kwargs)
    return mint.get_credit_report()


def initiate_account_refresh(email, password, **kwargs):
    mint = Mint(email=email, password=password, **kwargs)
    return mint.initiate_account_refresh()

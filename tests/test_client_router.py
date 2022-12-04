"""
Tests for the main Mint class

Verifies routing and instantiation in the presence of auth params
between browser and rest client - no endpoint testing
"""
import sys
import unittest
from unittest.mock import patch

import mintapi.browser
import pytest
from mintapi.api import Mint
from mintapi.browser import SeleniumBrowser
from mintapi.rest import RESTClient


class MintApiTests(unittest.TestCase):
    def test_fallback_browser_only(self):
        """
        if use_rest_client = False should not initialize the rest
        client and route all requests through the browser
        """
        api = Mint(use_rest_client=False)
        self.assertIsNone(api.rest_client)
        self.assertEqual(
            # main method all endpoint requests route through
            getattr(api, "request").__self__.__class__,
            SeleniumBrowser,
        )

    def test_initialization_with_auth_headers(self):
        """
        if use_rest_client = True and no auth should initialize the browser
        client and do nothing
        """
        api = Mint(use_rest_client=True, api_key="abc123", cookies="chocolate-chip")
        self.assertEqual(api.rest_client.__class__, RESTClient)
        self.assertEqual(
            # main method all endpoint requests route through
            getattr(api, "request").__self__.__class__,
            RESTClient,
        )
        self.assertIsNone(api.browser)

    def test_initialization_without_auth_headers(self):
        """
        if use_rest_client = True and no auth should initialize the browser
        client and do nothing if no driver params passed
        """
        api = Mint(use_rest_client=True)
        self.assertEqual(api.rest_client.__class__, RESTClient)
        self.assertEqual(
            # main method all endpoint requests route through
            getattr(api, "request").__self__.__class__,
            RESTClient,
        )
        self.assertEqual(api.browser.__class__, SeleniumBrowser)

    @patch.object(mintapi.browser.SeleniumBrowser, "_get_api_key_header")
    @patch.object(mintapi.browser.SeleniumBrowser, "_get_cookies")
    def test_auth_transfer(self, browser_cookie, browser_header):
        browser_header.return_value = {"authorization": "abc123"}
        browser_cookie.return_value = "fudge"
        api = Mint(use_rest_client=True)
        api.transfer_auth()
        self.assertEqual(api.rest_client.session.headers["authorization"], "abc123")
        self.assertEqual(api.rest_client.session.headers["cookie"], "fudge")

    def test_method_routing_with_rest_client(self):
        api = Mint(use_rest_client=True)
        for method in [
            i
            for i in dir(RESTClient)
            if not i.startswith("__") and i not in ("_abc_impl",)
        ]:
            self.assertEqual(
                getattr(api, method).__self__.__class__,
                RESTClient,
            )

    def test_method_routing_without_rest_client(self):
        api = Mint(use_rest_client=False)
        for method in [
            i
            for i in dir(SeleniumBrowser)
            if not i.startswith("__")
            and i not in ("_abc_impl", "driver", "status_message")
        ]:
            self.assertEqual(
                getattr(api, method).__self__.__class__,
                SeleniumBrowser,
            )

    def test_method_routing_with_nonsense_method(self):
        api = Mint(use_rest_client=True)
        with self.assertRaises(NotImplementedError):
            api.random_nonexistent_method()


if __name__ == "__main__":
    pytest.main(sys.argv)

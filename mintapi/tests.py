import copy
import datetime
import json
import unittest

import requests

try:
    from mock import patch  # Python 2
except ImportError:
    from unittest.mock import patch  # Python 3

import mintapi
import mintapi.api

accounts_example = [{
    "accountName": "Chase Checking",
    "lastUpdated": 1401201492000,
    "lastUpdatedInString": "25 minutes",
    "accountType": "bank",
    "currentBalance": 100.12,
}]


class Attribute:
    text = json.dumps({'response': {'42': {'response': accounts_example}}})


class Element:
    @staticmethod
    def get_attribute(test):
        return json.dumps({'token': '123'})


class TestMock:
    @staticmethod
    def find_element_by_name(test):
        return Element()

    @staticmethod
    def request(a, b, **c):
        return Attribute()


class MintApiTests(unittest.TestCase):
    @patch.object(mintapi.api, 'get_web_driver')
    def test_accounts(self, mock_driver):
        mock_driver.return_value = (TestMock(), "test")
        accounts = mintapi.get_accounts('foo', 'bar')

        self.assertFalse('lastUpdatedInDate' in accounts)
        self.assertNotEqual(accounts, accounts_example)

        accounts_annotated = copy.deepcopy(accounts_example)
        for account in accounts_annotated:
            account['lastUpdatedInDate'] = (datetime.datetime.fromtimestamp(account['lastUpdated'] / 1000))
        self.assertEqual(accounts, accounts_annotated)

        # ensure everything is json serializable as this is the command-line
        # behavior.
        mintapi.print_accounts(accounts)

    def test_chrome_driver_links(self):
        for platform in mintapi.api.CHROME_ZIP_TYPES:
            zip_type = mintapi.api.CHROME_ZIP_TYPES.get(platform)
            zip_file_url = mintapi.api.CHROME_DRIVER_BASE_URL % (mintapi.api.CHROME_DRIVER_VERSION, zip_type)
            request = requests.get(zip_file_url)
            self.assertEqual(request.status_code, 200)

    def test_parse_float(self):

        answer = mintapi.api.parse_float('10%')
        self.assertEqual(answer, float(10))

        answer = mintapi.api.parse_float('$10')
        self.assertEqual(answer, float(10))

        answer = mintapi.api.parse_float('0.00%')
        self.assertEqual(answer, float(0))

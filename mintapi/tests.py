import copy
import datetime
import json
import unittest

import pandas as pd

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

transactions_example = b'"Date","Description","Original Description","Amount","Transaction Type","Category","Account Name","Labels","Notes"\n"5/14/2020","Safeway","SAFEWAY.COM # 3031","88.09","debit","Groceries","CREDIT CARD","",""\n'


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
        latest_version = mintapi.api.get_latest_chrome_driver_version()
        for platform in mintapi.api.CHROME_ZIP_TYPES:
            request = requests.get(
                mintapi.api.get_chrome_driver_url(latest_version, platform))
            self.assertEqual(request.status_code, 200)

    def test_parse_float(self):

        answer = mintapi.api.parse_float('10%')
        self.assertEqual(answer, float(10))

        answer = mintapi.api.parse_float('$10')
        self.assertEqual(answer, float(10))

        answer = mintapi.api.parse_float('0.00%')
        self.assertEqual(answer, float(0))

    @patch.object(mintapi.Mint, 'get_transactions_csv')
    def test_get_transactions(self, mocked_get_transactions):
        mocked_get_transactions.return_value = transactions_example
        mint = mintapi.Mint()
        transactions_df = mint.get_transactions()
        assert(isinstance(transactions_df, pd.DataFrame))

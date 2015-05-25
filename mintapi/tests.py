import copy
import datetime
import json
import unittest

import mintapi
import mintapi.api

accounts_example = [{
    "accountName": "Chase Checking",
    "lastUpdated": 1401201492000,
    "lastUpdatedInString": "25 minutes",
    "accountType": "bank",
    "currentBalance": 100.12,
}]


class MockResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class MockSession(mintapi.api.Mint):
    def mount(self, *args, **kwargs):
        pass

    def get(self, path, data=None, headers=None):
        return MockResponse('')

    def post(self, path, data=None, headers=None):
        if 'loginUserSubmit' in path:
            text = {'sUser': {'token': 'foo'}}
        elif 'getUserPod' in path:
            text = {'userPN': 6}
        elif 'bundledServiceController' in path:
            data = json.loads(data['input'])[0]
            text = {'response': {data['id']: {'response': accounts_example}}}
        return MockResponse(json.dumps(text))


class MintApiTests(unittest.TestCase):
    def setUp(self):  # noqa
        self._Mint = mintapi.api.Mint
        mintapi.api.Mint = MockSession

    def tearDown(self):  # noqa
        mintapi.api.Mint = self._Mint

    def test_accounts(self):
        accounts = mintapi.get_accounts('foo', 'bar')

        self.assertFalse('lastUpdatedInDate' in accounts)
        self.assertNotEqual(accounts, accounts_example)

        accounts_annotated = copy.deepcopy(accounts_example)
        for account in accounts_annotated:
            account['lastUpdatedInDate'] = (datetime.datetime.fromtimestamp(
                                            account['lastUpdated']/1000))
        self.assertEqual(accounts, accounts_annotated)

        # ensure everything is json serializable as this is the command-line
        # behavior.
        mintapi.print_accounts(accounts)

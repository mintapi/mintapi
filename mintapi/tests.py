# coding=utf-8
import copy
import datetime
import json
import unittest

import mintapi
import mintapi.api


accounts_example = [
    {
        u"accountName": u"Chase Checking",
        u"lastUpdated": 1401201492000,
        u"lastUpdatedInString": u"25 minutes",
        u"accountType": u"bank",
        u"currentBalance": 100.12,
    },
]


class MockResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)

class MockSession(mintapi.api.Mint):
    def mount(self, *args, **kwargs):
        pass

    def request(self, method, url, data=None, headers=None, **kwargs):
        self.request_id += 1
        if 'loginUserSubmit' in url:
            text = {'sUser': {'token': 'foo'}}
        elif 'getUserPod' in url:
            text = {'userPN': 6}
        elif 'bundledServiceController' in url:
            data = json.loads(data['input'])[0]
            text = {'response': {data['id']: {'response': accounts_example}}}
        else:
            text = '{}'
        return MockResponse(json.dumps(text))


class MintApiTests(unittest.TestCase):
    def setUp(self):
        self._Mint = mintapi.api.Mint
        mintapi.api.Mint = MockSession

    def tearDown(self):
        mintapi.api.Mint = self._Mint

    def testAccounts(self):
        mint = mintapi.api.Mint('foo', 'bar')
        accounts = mint.get_accounts()

        self.assertFalse('lastUpdatedInDate' in accounts)
        self.assertNotEqual(accounts, accounts_example)

        accounts_annotated = copy.deepcopy(accounts_example)
        for account in accounts_annotated:
            account['lastUpdatedTs'] = account['lastUpdated']
            account['lastUpdated'] = datetime.datetime.fromtimestamp(account['lastUpdated'] / 1000)
        self.assertEqual(accounts, accounts_annotated)

        # ensure everything is json serializable as this is the command-line behavior.
        mintapi.print_accounts(accounts)




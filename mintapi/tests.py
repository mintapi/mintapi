import json
import unittest
import requests

import mintapi

accounts_example = [
  {
    "accountName": "Chase Checking", 
    "lastUpdatedInString": "25 minutes", 
    "accountType": "bank", 
    "currentBalance": 100.12,
  },
]

class MockResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

class MockSession:
    def mount(self, *args, **kwargs):
        pass

    def get(self, path, data=None, headers=None):
        return MockResponse('')

    def post(self, path, data=None, headers=None):
        if 'loginUserSubmit' in path:
            text = {'sUser': {'token': 'foo'}}
        elif 'bundledServiceController' in path:
            data = json.loads(data['input'])[0]
            text = {'response': {data['id']: {'response': accounts_example}}}
        return MockResponse(json.dumps(text))

class MintApiTests(unittest.TestCase):
    def setUp(self):
        self._Session = requests.Session
        requests.Session = MockSession

    def tearDown(self):
        requests.Session = self._Session

    def testAccounts(self):
        accounts = mintapi.get_accounts('foo', 'bar')
        self.assertEqual(accounts, accounts_example)

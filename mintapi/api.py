# coding=utf-8
"""Pull data from Mint"""
import datetime
import json

import requests
import xmltodict

from .utils import get_rnd, parse_float, convert_mint_transaction_dates_to_python_dates, convert_account_timestamps_to_python_dates





class Mint(requests.Session):
    def __init__(self, email, password):
        requests.Session.__init__(self)

        self.token = None
        self.request_id = 42  # magic number? random number?

        self.login_and_get_token(email, password)

    def request_json(self, method, url, **kwargs):
        """HTTP request with accepts json headers"""
        headers = {"accept": "application/json"}
        headers.update(kwargs.get('headers', {}))
        kwargs['headers'] = headers
        self.request_id += 1
        return self.request(method, url, **kwargs)

    def get_json(self, url, **kwargs):
        return self.request_json('GET', url, **kwargs)

    def post_json(self, url, **kwargs):
        return self.request_json('POST', url, **kwargs)

    def login_and_get_token(self, email, password):  
        # 0: Check to see if we're already logged in.
        if self.token:
            return

        # 1: Login.
        if self.get("https://wwws.mint.com/login.event?task=L").status_code != requests.codes.ok:
            raise Exception("Failed to load Mint login page")

        data = {'username': email}
        self.post_json('https://wwws.mint.com/getUserPod.xevent', data=data)

        data = {"username": email, "password": password, "task": "L", "browser": "firefox", "browserVersion": "27", "os": "linux"}
        response = self.post_json("https://wwws.mint.com/loginUserSubmit.xevent", data=data)

        if "token" not in response.text:
            raise Exception("Mint.com login failed[1]")

        # 2: Grab token.
        try:
            self.token = response.json()["sUser"]["token"]
        except LookupError:
            raise Exception("Mint.com login failed[2]")

    def get_accounts(self, get_detail=False):
        """Issue service request."""
        req_id = str(self.request_id)
        data = {
            "input": json.dumps(
                [{
                     "args": {
                         "types": [
                             "BANK",
                             "CREDIT",
                             "INVESTMENT",
                             "LOAN",
                             "MORTGAGE",
                             "OTHER_PROPERTY",
                             "REAL_ESTATE",
                             "VEHICLE",
                             "UNCLASSIFIED"
                         ]
                     },
                     "id": req_id,
                     "service": "MintAccountService",
                     "task": "getAccountsSorted"
                     # "task": "getAccountsSortedByBalanceDescending"
                 }]
            )
        }
        response = self.post_json("https://wwws.mint.com/bundledServiceController.xevent?legacy=false&token=" + self.token, data=data)
        if req_id not in response.text:
            raise Exception("Could not parse account data: " + response.text)

        # Parse the request
        accounts = response.json()["response"][req_id]["response"]

        # Return datetime objects for dates
        for account in accounts:
            convert_account_timestamps_to_python_dates(account)

        if get_detail:
            accounts = self.populate_extended_account_detail(accounts)
        return accounts

    def populate_extended_account_detail(self, accounts):
        """
        Populate extended account information

        I can't find any way to retrieve this information other than by
        doing this stupid one-call-per-account to listTransactions.xevent
        and parsing the HTML snippet :(
        """
        for account in accounts:
            headers = {'Referer': 'https://wwws.mint.com/transaction.event?accountId=' + str(account['id'])}
            url = 'https://wwws.mint.com/listTransaction.xevent?accountId=' + str(account['id']) + '&queryNew=&offset=0&comparableType=8&acctChanged=T&rnd=' + get_rnd()
            data = self.get_json(url, headers=headers).json()

            xml = '<div>' + data['accountHeader'] + '</div>'
            xml = xml.replace('&#8211;', '-')
            xml = xmltodict.parse(xml)

            account['availableMoney'] = None
            account['totalFees'] = None
            account['totalCredit'] = None
            account['nextPaymentAmount'] = None
            account['nextPaymentDate'] = None

            xml = xml['div']['div'][1]['table']
            if not 'tbody' not in xml:
                continue
            xml = xml['tbody']
            table_type = xml['@id']
            xml = xml['tr'][1]['td']

            if table_type == 'account-table-bank':
                account['availableMoney'] = parse_float(xml[1]['#text'])
                account['totalFees'] = parse_float(xml[3]['a']['#text'])
                if account['interestRate'] is None:
                    account['interestRate'] = parse_float(xml[2]['#text']) / 100.0
            elif table_type == 'account-table-credit':
                account['availableMoney'] = parse_float(xml[1]['#text'])
                account['totalCredit'] = parse_float(xml[2]['#text'])
                account['totalFees'] = parse_float(xml[4]['a']['#text'])
                if account['interestRate'] is None:
                    account['interestRate'] = parse_float(xml[3]['#text']) / 100.0
            elif table_type == 'account-table-loan':
                account['nextPaymentAmount'] = parse_float(xml[1]['#text'])
                account['nextPaymentDate'] = xml[2].get('#text', None)
            elif table_type == 'account-type-investment':
                account['totalFees'] = parse_float(xml[2]['a']['#text'])

        return accounts

    def get_categories(self):  
        # Get category metadata.
        req_id = str(self.request_id)
        data = {
            'input': json.dumps(
                [{
                     'args': {
                         'excludedCategories': [],
                         'sortByPrecedence': False,
                         'categoryTypeFilter': 'FREE'
                     },
                     'id': req_id,
                     'service': 'MintCategoryService',
                     'task': 'getCategoryTreeDto2'
                 }]
            )
        }
        response = self.post_json('https://wwws.mint.com/bundledServiceController.xevent?legacy=false&token=' + self.token, data=data)
        if req_id not in response.text:
            raise Exception('Could not parse category data: "' + response.text + '"')
        response = response.json()['response'][req_id]['response']

        # Build category list 
        categories = {}
        for category in response['allCategories']:
            if category['parentId'] == 0:
                continue
            categories[category['id']] = category

        return categories

    def get_budgets(self):
        categories = self.get_categories()

        # Issue request for budget utilization
        today = datetime.date.today()
        this_month = datetime.date(today.year, today.month, 1)
        last_year = this_month - datetime.timedelta(days=330)
        this_month = str(this_month.month).zfill(2) + '/01/' + str(this_month.year)
        last_year = str(last_year.month).zfill(2) + '/01/' + str(last_year.year)
        json_data = self.get_json('https://wwws.mint.com/getBudget.xevent?startDate=' + last_year + '&endDate=' + this_month + '&rnd=' + get_rnd()).json()

        # Make the skeleton return structure
        budgets = {
            'income': json_data['data']['income'][str(max(map(int, json_data['data']['income'].keys())))]['bu'],
            'spend': json_data['data']['spending'][str(max(map(int, json_data['data']['income'].keys())))]['bu']
        }

        # Fill in the return structure
        for direction in budgets.keys():
            for budget in budgets[direction]:
                budget['cat'] = categories[budget['cat']]

        return budgets

    def initiate_account_refresh(self):
        """ Submit refresh request. """
        self.post_json('https://wwws.mint.com/refreshFILogins.xevent', data={'token': self.token})

    def get_transaction_count(self):
        """Get number of available transactions"""
        transactions_count_url = 'https://wwws.mint.com/listTransaction.xevent?queryNew=&offset=0&filterType=cash&comparableType=8'
        count_json = self.get_json(transactions_count_url).json()
        return count_json['count']

    def get_transactions(self, limit=None):
        """Get transaction records"""
        limit = limit or self.get_transaction_count()
        url = "https://wwws.mint.com/app/getJsonData.xevent?accountId=0&queryNew=&offset={offset}&acctChanged=T&task=transactions,merchants,txnfilters"

        transactions = []
        for offset in xrange(0, limit, 50):
            json_data = self.get_json(url.format(offset=offset)).json()
            transactions += json_data['set'][0]['data']

        for transaction in transactions:
            convert_mint_transaction_dates_to_python_dates(transaction)
            transaction['amount'] = parse_float(transaction['amount'])

        return transactions
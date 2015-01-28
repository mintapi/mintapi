# coding=utf-8
"""Pull data from Mint"""
import datetime
import json

import requests
import xmltodict

from utils import get_rnd, parse_float


DATE_FIELDS = [
    'addAccountDate',
    'closeDate',
    'fiLastUpdated',
    'lastUpdated',
]


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
        return self.request(method, url, **kwargs)

    def get_json(self, url, **kwargs):
        return self.request_json('GET', url, **kwargs)

    def post_json(self, url, **kwargs):
        return self.request_json('POST', url, **kwargs)

    @classmethod
    def create(cls, email, password):  
        return Mint(email, password)

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

        if not response.json()["sUser"]["token"]:
            raise Exception("Mint.com login failed[2]")

        # 2: Grab token.
        self.token = response["sUser"]["token"]

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
        self.request_id += 1
        if req_id not in response.text:
            raise Exception("Could not parse account data: " + response.text)

        # Parse the request
        accounts = response.json()["response"][req_id]["response"]

        # Return datetime objects for dates
        for account in accounts:
            for df in DATE_FIELDS:
                if df in account:
                    # Convert from javascript timestamp to unix timestamp
                    # http://stackoverflow.com/a/9744811/5026
                    try:
                        ts = account[df] / 1e3
                    except TypeError:
                        # returned data is not a number, don't parse
                        continue
                    account[df + 'InDate'] = datetime.datetime.fromtimestamp(ts)
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
        response = self.post_json('https://wwws.mint.com/bundledServiceController.xevent?legacy=false&token=' + self.token, data=data).text
        self.request_id += 1
        if req_id not in response:
            raise Exception('Could not parse category data: "' + response + '"')
        response = json.loads(response)
        response = response['response'][req_id]['response']

        # Build category list 
        categories = {}
        for category in response['allCategories']:
            if category['parentId'] == 0:
                continue
            categories[category['id']] = category

        return categories

    def get_budgets(self):
        # Get categories
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


def get_accounts(email, password, get_detail=False):
    return Mint(email, password).get_accounts(get_detail=get_detail)


def make_accounts_presentable(accounts):
    for account in accounts:
        for k, v in account.items():
            if isinstance(v, datetime.datetime):
                account[k] = repr(v)
    return accounts


def print_accounts(accounts):
    print(json.dumps(make_accounts_presentable(accounts), indent=2))


def get_budgets(email, password):
    return Mint(email, password).get_budgets()


def initiate_account_refresh(email, password):
    Mint(email, password).initiate_account_refresh()


def main():
    import getpass
    import optparse

    # Parse command-line arguments {{{
    cmdline = optparse.OptionParser(usage='usage: %prog [options] email password')
    cmdline.add_option('--accounts', action='store_true', dest='accounts', default=False, help='Retrieve account information (default if nothing else is specified)')
    cmdline.add_option('--budgets', action='store_true', dest='budgets', default=False, help='Retrieve budget information')
    cmdline.add_option('--extended-accounts', action='store_true', dest='accounts_ext', default=False, help='Retrieve extended account information (slower, implies --accounts)')

    (options, args) = cmdline.parse_args()

    # Handle Python 3's raw_input change.
    try:
        input = raw_input
    except NameError:
        pass

    if len(args) >= 2:
        (email, password) = args[0:1]
    else:
        email = input("Mint email: ")
        password = getpass.getpass("Password: ")

    if options.accounts_ext:
        options.accounts = True

    if not (options.accounts or options.budgets):
        options.accounts = True

    mint = Mint(email, password)

    data = None
    if options.accounts and options.budgets:
        try:
            accounts = make_accounts_presentable(mint.get_accounts(get_detail=options.accounts_ext))
        except:
            accounts = None

        try:
            budgets = mint.get_budgets()
        except:
            budgets = None

        data = {'accounts': accounts, 'budgets': budgets}
    elif options.budgets:
        try:
            data = mint.get_budgets()
        except:
            data = None
    elif options.accounts:
        try:
            data = make_accounts_presentable(mint.get_accounts(get_detail=options.accounts_ext))
        except:
            data = None

    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()

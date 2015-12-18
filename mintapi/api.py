import json
import random
import time

try:
    from StringIO import StringIO  # Python 2
except ImportError:
    from io import BytesIO as StringIO  # Python 3

from datetime import date, datetime, timedelta

import requests

from requests.adapters import HTTPAdapter
try:
        from requests.packages.urllib3.poolmanager import PoolManager
except:
        from urllib3.poolmanager import PoolManager

import xmltodict

try:
    import pandas as pd
except ImportError:
    pd = None


def assert_pd():
    # Common function to check if pd is installed
    if not pd:
        raise ImportError(
            'transactions data requires pandas; '
            'please pip install pandas'
        )

DATE_FIELDS = [
    'addAccountDate',
    'closeDate',
    'fiLastUpdated',
    'lastUpdated',
]


class MintHTTPSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, **kwargs):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize, **kwargs)


class Mint(requests.Session):
    json_headers = {'accept': 'application/json'}
    request_id = 42  # magic number? random number?
    token = None

    def __init__(self, email=None, password=None):
        requests.Session.__init__(self)
        self.mount('https://', MintHTTPSAdapter())
        if email and password:
            self.login_and_get_token(email, password)

    @classmethod
    def create(cls, email, password):  # {{{
        mint = Mint()
        mint.login_and_get_token(email, password)
        return mint

    @classmethod
    def get_rnd(cls):  # {{{
        return (str(int(time.mktime(datetime.now().timetuple())))
                + str(random.randrange(999)).zfill(3))

    @classmethod
    def parse_float(cls, string):  # {{{
        for bad_char in ['$', ',', '%']:
            string = string.replace(bad_char, '')

        try:
            return float(string)
        except ValueError:
            return None

    def request_and_check(self, url, method='get',
                          expected_content_type=None, **kwargs):
        """Performs a request, and checks that the status is OK, and that the
        content-type matches expectations.

        Args:
          url: URL to request
          method: either 'get' or 'post'
          expected_content_type: prefix to match response content-type against
          **kwargs: passed to the request method directly.

        Raises:
          RuntimeError if status_code does not match.
        """
        assert (method == 'get' or method == 'post')
        result = getattr(self, method)(url, **kwargs)
        if result.status_code != requests.codes.ok:
            raise RuntimeError('Error requesting %r, status = %d' %
                               (url, result.status_code))
        if expected_content_type is not None:
            content_type = result.headers.get('content-type', '')
            if not content_type.startswith(expected_content_type):
                raise RuntimeError(
                    'Error requesting %r, content type %r does not match %r' %
                    (url, content_type, expected_content_type))
        return result

    def login_and_get_token(self, email, password):  # {{{
        # 0: Check to see if we're already logged in.
        if self.token is not None:
            return

        # 1: Login.
        login_url = 'https://wwws.mint.com/login.event?task=L'
        try:
            self.request_and_check(login_url)
        except RuntimeError:
            raise Exception('Failed to load Mint login page')

        data = {'username': email}
        response = self.post('https://wwws.mint.com/getUserPod.xevent',
                             data=data, headers=self.json_headers).text

        data = {'username': email, 'password': password, 'task': 'L',
                'browser': 'firefox', 'browserVersion': '27', 'os': 'linux'}
        response = self.post('https://wwws.mint.com/loginUserSubmit.xevent',
                             data=data, headers=self.json_headers).text

        if 'token' not in response:
            raise Exception('Mint.com login failed[1]')

        response = json.loads(response)
        if not response['sUser']['token']:
            raise Exception('Mint.com login failed[2]')

        # 2: Grab token.
        self.token = response['sUser']['token']

    def get_accounts(self, get_detail=False):  # {{{
        # Issue service request.
        req_id = str(self.request_id)

        input = {
            'args': {
                'types': [
                    'BANK',
                    'CREDIT',
                    'INVESTMENT',
                    'LOAN',
                    'MORTGAGE',
                    'OTHER_PROPERTY',
                    'REAL_ESTATE',
                    'VEHICLE',
                    'UNCLASSIFIED'
                ]
            },
            'id': req_id,
            'service': 'MintAccountService',
            'task': 'getAccountsSorted'
            # 'task': 'getAccountsSortedByBalanceDescending'
        }

        data = {'input': json.dumps([input])}
        account_data_url = ('https://wwws.mint.com/bundledServiceController.'
                            'xevent?legacy=false&token=' + self.token)
        response = self.post(account_data_url, data=data,
                             headers=self.json_headers).text
        self.request_id = self.request_id + 1
        if req_id not in response:
            raise Exception('Could not parse account data: ' + response)

        # Parse the request
        response = json.loads(response)
        accounts = response['response'][req_id]['response']

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
                    account[df + 'InDate'] = datetime.fromtimestamp(ts)
        if get_detail:
            accounts = self.populate_extended_account_detail(accounts)
        return accounts

    def set_user_property(self, name, value):
        url = ('https://wwws.mint.com/bundledServiceController.xevent?' +
               'legacy=false&token=' + self.token)
        req_id = str(self.request_id)
        self.request_id += 1
        result = self.post(
            url,
            data={'input': json.dumps([{'args': {'propertyName': name,
                                                 'propertyValue': value},
                                        'service': 'MintUserService',
                                        'task': 'setUserProperty',
                                        'id': req_id}])},
            headers=self.json_headers)
        if result.status_code != 200:
            raise Exception('Received HTTP error %d' % result.status_code)
        response = result.text
        if req_id not in response:
            raise Exception("Could not parse response to set_user_property")

    def _dateconvert(self, dateraw):
        # Converts dates from json data
        cy = datetime.isocalendar(date.today())[0]
        try:
            newdate = datetime.strptime(dateraw + str(cy), '%b %d%Y')
        except:
            newdate = datetime.strptime(dateraw, '%m/%d/%y')
        return newdate

    def _debit_credit(self, row):
        # Reverses credit balances
        dic = {False: -1, True: 1}
        return float(row['amount'][1:].replace(',', '')) * dic[row['isDebit']]

    def get_transactions_json(self, include_investment=False,
                              skip_duplicates=False, start_date=None):
        """Returns the raw JSON transaction data as downloaded from Mint.  The JSON
        transaction data includes some additional information missing from the
        CSV data, such as whether the transaction is pending or completed, but
        leaves off the year for current year transactions.

        Warning: In order to reliably include or exclude duplicates, it is
        necessary to change the user account property 'hide_duplicates' to the
        appropriate value.  This affects what is displayed in the web
        interface.  Note that the CSV transactions never exclude duplicates.
        """

        # Warning: This is a global property for the user that we are changing.
        self.set_user_property('hide_duplicates',
                               'T' if skip_duplicates else 'F')

        # Converts the start date into datetime format - must be mm/dd/yy
        try:
            start_date = datetime.strptime(start_date, '%m/%d/%y')
        except:
            start_date = None

        all_txns = []
        offset = 0
        # Mint only returns some of the transactions at once.  To get all of
        # them, we have to keep asking for more until we reach the end.
        while 1:
            # Specifying accountId=0 causes Mint to return investment
            # transactions as well.  Otherwise they are skipped by
            # default.
            url = (
                'https://wwws.mint.com/getJsonData.xevent?' +
                'queryNew=&offset={offset}&comparableType=8&' +
                'rnd={rnd}&{query_options}').format(
                    offset=offset,
                    rnd=Mint.get_rnd(),
                    query_options=(
                        'accountId=0&task=transactions' if include_investment
                        else 'task=transactions,txnfilters&filterType=cash'))
            result = self.request_and_check(
                url, headers=self.json_headers,
                expected_content_type='text/json')
            data = json.loads(result.text)
            txns = data['set'][0].get('data', [])
            df = pd.DataFrame(txns)
            if start_date:
                dates = list(df['odate'])
                last_dt = self._dateconvert(dates[-1])
                if last_dt < start_date:
                    keep_txns = []
                    for item in txns:
                        if self._dateconvert(item['odate']) >= start_date:
                            keep_txns.append(item)
                    all_txns.extend(keep_txns)
                    break
            if not txns:
                break
            all_txns.extend(txns)
            offset += len(txns)
        return all_txns

    def get_detailed_transactions(self, include_investment=False,
                                  skip_duplicates=False,
                                  remove_pending=True,
                                  start_date=None):
        """Returns the JSON transaction data as a DataFrame, and converts
        current year dates and prior year dates into consistent datetime
        format, and reverses credit activity.

        Note: start_date must be in format mm/dd/yy. If pulls take too long,
        use a more recent start date. See json explanations of
        include_investment and skip_duplicates.

        Also note: Mint includes pending transactions, however these sometimes
        change dates/amounts after the transactions post. They have been
        removed by default in this pull, but can be included by changing
        remove_pending to False

        """
        assert_pd()

        result = self.get_transactions_json(include_investment,
                                            skip_duplicates, start_date)
        df = pd.DataFrame(result)
        df['odate'] = df['odate'].apply(self._dateconvert)

        if remove_pending:
            df = df[~df.isPending]
            df.reset_index(drop=True, inplace=True)

        df.amount = df.apply(self._debit_credit, axis=1)

        return df

    def get_transactions_csv(self, include_investment=False):
        """Returns the raw CSV transaction data as downloaded from Mint.

        If include_investment == True, also includes transactions that Mint
        classifies as investment-related.  You may find that the investment
        transaction data is not sufficiently detailed to actually be useful,
        however.
        """

        # Specifying accountId=0 causes Mint to return investment
        # transactions as well.  Otherwise they are skipped by
        # default.
        result = self.request_and_check(
            'https://wwws.mint.com/transactionDownload.event' +
            ('?accountId=0' if include_investment else ''),
            headers=self.headers,
            expected_content_type='text/csv'
            )
        return result.content

    def get_net_worth(self, account_data=None):
        if account_data is None:
            account_data = self.get_accounts()

        # account types in this list will be subtracted
        negative_accounts = ['loan', 'loans', 'credit']
        try:
            net_worth = long()
        except NameError:
            net_worth = 0

        # iterate over accounts and add or subtract account balances
        for account in [a for a in account_data if a['isActive']]:
            current_balance = account['currentBalance']
            if account['accountType'] in negative_accounts:
                net_worth -= current_balance
            else:
                net_worth += current_balance
        return net_worth

    def get_transactions(self):
        """Returns the transaction data as a Pandas DataFrame.
        """
        assert_pd()
        s = StringIO(self.get_transactions_csv())
        s.seek(0)
        df = pd.read_csv(s, parse_dates=['Date'])
        df.columns = [c.lower().replace(' ', '_') for c in df.columns]
        df.category = (df.category.str.lower()
                       .replace('uncategorized', pd.np.nan))
        return df

    def populate_extended_account_detail(self, accounts):  # {{{
        # I can't find any way to retrieve this information other than by
        # doing this stupid one-call-per-account to listTransactions.xevent
        # and parsing the HTML snippet :(
        for account in accounts:
            headers = self.json_headers
            headers['Referer'] = ('https://wwws.mint.com/transaction.event?'
                                  'accountId=' + str(account['id']))

            list_txn_url = ('https://wwws.mint.com/listTransaction.xevent?'
                            'accountId=' + str(account['id']) + '&queryNew=&'
                            'offset=0&comparableType=8&acctChanged=T&rnd=' +
                            Mint.get_rnd())

            response = json.loads(self.get(list_txn_url, headers=headers).text)
            xml = '<div>' + response['accountHeader'] + '</div>'
            xml = xml.replace('&#8211;', '-')
            xml = xmltodict.parse(xml)

            account['availableMoney'] = None
            account['totalFees'] = None
            account['totalCredit'] = None
            account['nextPaymentAmount'] = None
            account['nextPaymentDate'] = None

            xml = xml['div']['div'][1]['table']
            if 'tbody' not in xml:
                continue
            xml = xml['tbody']
            table_type = xml['@id']
            xml = xml['tr'][1]['td']

            if table_type == 'account-table-bank':
                account['availableMoney'] = Mint.parse_float(xml[1]['#text'])
                account['totalFees'] = Mint.parse_float(xml[3]['a']['#text'])
                if (account['interestRate'] is None):
                    account['interestRate'] = (
                        Mint.parse_float(xml[2]['#text']) / 100.0
                    )
            elif table_type == 'account-table-credit':
                account['availableMoney'] = Mint.parse_float(xml[1]['#text'])
                account['totalCredit'] = Mint.parse_float(xml[2]['#text'])
                account['totalFees'] = Mint.parse_float(xml[4]['a']['#text'])
                if account['interestRate'] is None:
                    account['interestRate'] = (
                        Mint.parse_float(xml[3]['#text']) / 100.0
                    )
            elif table_type == 'account-table-loan':
                account['nextPaymentAmount'] = (
                    Mint.parse_float(xml[1]['#text'])
                )
                account['nextPaymentDate'] = xml[2].get('#text', None)
            elif table_type == 'account-type-investment':
                account['totalFees'] = Mint.parse_float(xml[2]['a']['#text'])

        return accounts

    def get_categories(self):  # {{{
        # Get category metadata.
        req_id = str(self.request_id)
        data = {
            'input': json.dumps([{
                'args': {
                    'excludedCategories': [],
                    'sortByPrecedence': False,
                    'categoryTypeFilter': 'FREE'
                },
                'id': req_id,
                'service': 'MintCategoryService',
                'task': 'getCategoryTreeDto2'
            }])
        }

        cat_url = ('https://wwws.mint.com/bundledServiceController.xevent'
                   '?legacy=false&token=' + self.token)
        response = self.post(cat_url, data=data,
                             headers=self.json_headers).text
        self.request_id = self.request_id + 1
        if req_id not in response:
            raise Exception('Could not parse category data: "'
                            + response + '"')
        response = json.loads(response)
        response = response['response'][req_id]['response']

        # Build category list
        categories = {}
        for category in response['allCategories']:
            if category['parentId'] == 0:
                continue
            categories[category['id']] = category

        return categories

    def get_budgets(self):  # {{{

        # Get categories
        categories = self.get_categories()

        # Issue request for budget utilization
        today = date.today()
        this_month = date(today.year, today.month, 1)
        last_year = this_month - timedelta(days=330)
        this_month = (str(this_month.month).zfill(2) +
                      '/01/' + str(this_month.year))
        last_year = (str(last_year.month).zfill(2) +
                     '/01/' + str(last_year.year))
        response = json.loads(self.get(
            'https://wwws.mint.com/getBudget.xevent?startDate=' + last_year +
            '&endDate=' + this_month + '&rnd=' + Mint.get_rnd(),
            headers=self.json_headers
        ).text)

        # Make the skeleton return structure
        budgets = {
            'income': response['data']['income'][
                str(max(map(int, response['data']['income'].keys())))
            ]['bu'],
            'spend': response['data']['spending'][
                str(max(map(int, response['data']['income'].keys())))
            ]['bu']
        }

        # Fill in the return structure
        for direction in budgets.keys():
            for budget in budgets[direction]:
                budget['cat'] = self.get_category_from_id(
                    budget['cat'],
                    categories
                )

        return budgets

    def get_category_from_id(self, cid, categories):
        if cid == 0:
            return 'Uncategorized'

        for i in categories:
            if categories[i]['id'] == cid:
                return categories[i]['name']

            if 'children' in categories[i]:
                for j in categories[i]['children']:
                    if categories[i][j]['id'] == cid:
                        return categories[i][j]['name']

        return 'Unknown'

    def initiate_account_refresh(self):
        # Submit refresh request.
        data = {
            'token': self.token
        }
        self.post('https://wwws.mint.com/refreshFILogins.xevent',
                  data=data, headers=self.json_headers)


def get_accounts(email, password, get_detail=False):
    mint = Mint.create(email, password)
    return mint.get_accounts(get_detail=get_detail)


def get_net_worth(email, password):
    mint = Mint.create(email, password)
    account_data = mint.get_accounts()
    return mint.get_net_worth(account_data)


def make_accounts_presentable(accounts):
    for account in accounts:
        for k, v in account.items():
            if isinstance(v, datetime):
                account[k] = repr(v)
    return accounts


def print_accounts(accounts):
    print(json.dumps(make_accounts_presentable(accounts), indent=2))


def get_budgets(email, password):
    mint = Mint.create(email, password)
    return mint.get_budgets()


def initiate_account_refresh(email, password):
    mint = Mint.create(email, password)
    return mint.initiate_account_refresh()


def main():
    import getpass
    import argparse

    try:
        import keyring
    except ImportError:
        keyring = None

    # Parse command-line arguments {{{
    cmdline = argparse.ArgumentParser()
    cmdline.add_argument('email', nargs='?', default=None,
                         help='The e-mail address for your Mint.com account')
    cmdline.add_argument('password', nargs='?', default=None,
                         help='The password for your Mint.com account')
    cmdline.add_argument('--accounts', action='store_true', dest='accounts',
                         default=False, help='Retrieve account information'
                         ' (default if nothing else is specified)')
    cmdline.add_argument('--budgets', action='store_true', dest='budgets',
                         default=False, help='Retrieve budget information')
    cmdline.add_argument('--net-worth', action='store_true', dest='net_worth',
                         default=False, help='Retrieve net worth information')
    cmdline.add_argument('--extended-accounts', action='store_true',
                         dest='accounts_ext', default=False,
                         help='Retrieve extended account information (slower, '
                         'implies --accounts)')
    cmdline.add_argument('--transactions', '-t', action='store_true',
                         default=False, help='Retrieve transactions')
    cmdline.add_argument('--filename', '-f', help='write results to file. can '
                         'be {csv,json} format. default is to write to '
                         'stdout.')
    cmdline.add_argument('--keyring', action='store_true',
                         help='Use OS keyring for storing password '
                         'information')

    options = cmdline.parse_args()

    if options.keyring and not keyring:
        cmdline.error('--keyring can only be used if the `keyring` '
                      'library is installed.')

    try:
        from __builtin__ import raw_input as input
    except NameError:
        pass

    # Try to get the e-mail and password from the arguments
    email = options.email
    password = options.password

    if not email:
        # If the user did not provide an e-mail, prompt for it
        email = input("Mint e-mail: ")

    if keyring and not password:
        # If the keyring module is installed and we don't yet have
        # a password, try prompting for it
        password = keyring.get_password('mintapi', email)

    if not password:
        # If we still don't have a password, prompt for it
        password = getpass.getpass("Mint password: ")

    if options.keyring:
        # If keyring option is specified, save the password in the keyring
        keyring.set_password('mintapi', email, password)

    if options.accounts_ext:
        options.accounts = True

    if not any([options.accounts, options.budgets, options.transactions,
                options.net_worth]):
        options.accounts = True

    mint = Mint.create(email, password)

    data = None
    if options.accounts and options.budgets:
        try:
            accounts = make_accounts_presentable(
                mint.get_accounts(get_detail=options.accounts_ext)
            )
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
            data = make_accounts_presentable(mint.get_accounts(
                get_detail=options.accounts_ext)
            )
        except:
            data = None
    elif options.transactions:
        data = mint.get_transactions()
    elif options.net_worth:
        data = mint.get_net_worth()

    # output the data
    if options.transactions:
        if options.filename is None:
            print(data.to_json(orient='records'))
        elif options.filename.endswith('.csv'):
            data.to_csv(options.filename, index=False)
        elif options.filename.endswith('.json'):
            data.to_json(options.filename, orient='records')
        else:
            raise ValueError('file extension must be either .csv or .json')
    else:
        if options.filename is None:
            print(json.dumps(data, indent=2))
        elif options.filename.endswith('.json'):
            with open(options.filename, 'w+') as f:
                json.dump(data, f, indent=2)
        else:
            raise ValueError('file type must be json for non-transaction data')

if __name__ == '__main__':
    main()

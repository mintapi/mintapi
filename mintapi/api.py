import atexit
from datetime import date, datetime, timedelta
import io
import json
import os
import os.path
import random
import re
import requests
from sys import platform as _platform
import time
import warnings
import zipfile

try:
    from StringIO import StringIO  # Python 2
except ImportError:
    from io import BytesIO as StringIO  # Python 3

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver import ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from seleniumrequests import Chrome
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


def json_date_to_datetime(dateraw):
    cy = datetime.isocalendar(date.today())[0]
    try:
        newdate = datetime.strptime(dateraw + str(cy), '%b %d%Y')
    except:
        newdate = datetime.strptime(dateraw, '%m/%d/%y')
    return newdate


def reverse_credit_amount(row):
    amount = float(row['amount'][1:].replace(',', ''))
    return amount if row['isDebit'] else -amount


CHROME_DRIVER_VERSION = 2.41
CHROME_DRIVER_BASE_URL = 'https://chromedriver.storage.googleapis.com/%s/chromedriver_%s.zip'
CHROME_ZIP_TYPES = {
    'linux': 'linux64',
    'linux2': 'linux64',
    'darwin': 'mac64',
    'win32': 'win32',
    'win64': 'win32'
}

def get_web_driver(email, password, headless=False, mfa_method=None,
                   mfa_input_callback=None, wait_for_sync=True):
    if headless and mfa_method is None:
        warnings.warn("Using headless mode without specifying an MFA method"
                      "is unlikely to lead to a successful login. Defaulting --mfa-method=sms")
        mfa_method = "sms"

    zip_type = ""
    executable_path = os.getcwd() + os.path.sep + 'chromedriver'
    if _platform in ['win32', 'win64']:
        executable_path += '.exe'

    zip_type = CHROME_ZIP_TYPES.get(_platform)

    if not os.path.exists(executable_path):
        zip_file_url = CHROME_DRIVER_BASE_URL % (CHROME_DRIVER_VERSION, zip_type)
        request = requests.get(zip_file_url)

        if request.status_code != 200:
            raise RuntimeError('Error finding chromedriver at %r, status = %d' %
                               (zip_file_url, request.status_code))

        zip_file = zipfile.ZipFile(io.BytesIO(request.content))
        zip_file.extractall()
        os.chmod(executable_path, 0o755)

    chrome_options = ChromeOptions()
    if headless:
        chrome_options.add_argument('headless')
        chrome_options.add_argument('no-sandbox')
        chrome_options.add_argument('disable-dev-shm-usage')
        chrome_options.add_argument('disable-gpu')
        # chrome_options.add_argument("--window-size=1920x1080")

    driver = Chrome(chrome_options=chrome_options, executable_path="%s" % executable_path)
    driver.get("https://www.mint.com")
    driver.implicitly_wait(20)  # seconds
    driver.find_element_by_link_text("Log In").click()

    driver.find_element_by_id("ius-userid").send_keys(email)
    driver.find_element_by_id("ius-password").send_keys(password)
    driver.find_element_by_id("ius-sign-in-submit-btn").submit()

    # Wait until logged in, just in case we need to deal with MFA.
    while not driver.current_url.startswith(
            'https://mint.intuit.com/overview.event'):
        time.sleep(1)

        driver.implicitly_wait(1)  # seconds
        try:
            driver.find_element_by_id('ius-mfa-options-form')
            try:
                mfa_method_option = driver.find_element_by_id('ius-mfa-option-{}'.format(mfa_method))
                mfa_method_option.click()
                mfa_method_submit = driver.find_element_by_id("ius-mfa-options-submit-btn")
                mfa_method_submit.click()

                mfa_code = (mfa_input_callback or input)("Please enter your 6-digit MFA code: ")
                mfa_code_input = driver.find_element_by_id("ius-mfa-confirm-code")
                mfa_code_input.send_keys(mfa_code)

                mfa_code_submit = driver.find_element_by_id("ius-mfa-otp-submit-btn")
                mfa_code_submit.click()
            except Exception:  # if anything goes wrong for any reason, give up on MFA
                mfa_method = None
                warnings.warn("Giving up on handling MFA. Please complete "
                              "the MFA process manually in the browser.")
        except NoSuchElementException:
            pass
        finally:
            driver.implicitly_wait(20)  # seconds

    # Wait until the overview page has actually loaded, and if wait_for_sync==True, sync has completed.
    if wait_for_sync:
        status_message = driver.find_element_by_css_selector(".SummaryView .message")
        try:
            WebDriverWait(driver, 5 * 60).until(
                lambda x: "Account refresh complete" in status_message.get_attribute('innerHTML')
            )
        except TimeoutException:
            warnings.warn("Mint sync apparently incomplete after 5 minutes. Data "
                          "retrieved may not be current.")
    else:
        driver.find_element_by_id("transaction")

    return driver


IGNORE_FLOAT_REGEX = re.compile(r"[$,%]")


def parse_float(str_number):
    try:
        return float(IGNORE_FLOAT_REGEX.sub('', str_number))
    except ValueError:
        return None


DATE_FIELDS = [
    'addAccountDate',
    'closeDate',
    'fiLastUpdated',
    'lastUpdated',
]


def convert_account_dates_to_datetime(account):
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


MINT_ROOT_URL = 'https://mint.intuit.com'
MINT_ACCOUNTS_URL = 'https://accounts.intuit.com'

JSON_HEADER = {'accept': 'application/json'}


class MintException(Exception):
    pass


class Mint(object):
    request_id = 42  # magic number? random number?
    token = None
    driver = None

    def __init__(self, email=None, password=None, mfa_method=None,
                 mfa_input_callback=None, headless=False):
        if email and password:
            self.login_and_get_token(email, password,
                                     mfa_method=mfa_method,
                                     mfa_input_callback=mfa_input_callback,
                                     headless=headless)

    @classmethod
    def create(cls, email, password, **opts):
        return Mint(email, password, **opts)

    @classmethod
    def get_rnd(cls):  # {{{
        return (str(int(time.mktime(datetime.now().timetuple()))) +
                str(random.randrange(999)).zfill(3))

    def close(self):
        """Logs out and quits the current web driver/selenium session."""
        if not self.driver:
            return

        try:
            self.driver.implicitly_wait(1)
            self.driver.find_element_by_id('link-logout').click()
        except:
            pass

        self.driver.quit()
        self.driver = None

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
        assert method in ['get', 'post']
        result = self.driver.request(method, url, **kwargs)
        if result.status_code != requests.codes.ok:
            raise RuntimeError('Error requesting %r, status = %d' %
                               (url, result.status_code))
        if expected_content_type is not None:
            content_type = result.headers.get('content-type', '')
            if not re.match(expected_content_type, content_type):
                raise RuntimeError(
                    'Error requesting %r, content type %r does not match %r' %
                    (url, content_type, expected_content_type))
        return result

    def get(self, url, **kwargs):
        return self.driver.request('GET', url, **kwargs)

    def post(self, url, **kwargs):
        return self.driver.request('POST', url, **kwargs)

    def login_and_get_token(self, email, password, mfa_method=None,
                            mfa_input_callback=None, headless=False):
        if self.token and self.driver:
            return

        self.driver = get_web_driver(email, password,
                                     mfa_method=mfa_method,
                                     mfa_input_callback=mfa_input_callback,
                                     headless=headless)
        self.token = self.get_token()

    def get_token(self):
        value_json = self.driver.find_element_by_name(
            'javascript-user').get_attribute('value')
        return json.loads(value_json)['token']

    def get_request_id_str(self):
        req_id = self.request_id
        self.request_id += 1
        return str(req_id)

    def get_accounts(self, get_detail=False):  # {{{
        # Issue service request.
        req_id = self.get_request_id_str()

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
        account_data_url = (
            '{}/bundledServiceController.xevent?legacy=false&token={}'.format(
                MINT_ROOT_URL, self.token))
        response = self.post(
            account_data_url,
            data=data,
            headers=JSON_HEADER
        ).text
        if req_id not in response:
            raise MintException('Could not parse account data: ' + response)

        # Parse the request
        response = json.loads(response)
        accounts = response['response'][req_id]['response']

        for account in accounts:
            convert_account_dates_to_datetime(account)

        if get_detail:
            accounts = self.populate_extended_account_detail(accounts)

        return accounts

    def set_user_property(self, name, value):
        url = (
            '{}/bundledServiceController.xevent?legacy=false&token={}'.format(
                MINT_ROOT_URL, self.token))
        req_id = self.get_request_id_str()
        result = self.post(
            url,
            data={'input': json.dumps([{'args': {'propertyName': name,
                                                 'propertyValue': value},
                                        'service': 'MintUserService',
                                        'task': 'setUserProperty',
                                        'id': req_id}])},
            headers=JSON_HEADER)
        if result.status_code != 200:
            raise MintException('Received HTTP error %d' % result.status_code)
        response = result.text
        if req_id not in response:
            raise MintException(
                'Could not parse response to set_user_property')

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
        self.set_user_property(
            'hide_duplicates', 'T' if skip_duplicates else 'F')

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
                MINT_ROOT_URL +
                '/getJsonData.xevent?' +
                'queryNew=&offset={offset}&comparableType=8&' +
                'rnd={rnd}&{query_options}').format(
                offset=offset,
                rnd=Mint.get_rnd(),
                query_options=(
                    'accountId=0&task=transactions' if include_investment
                    else 'task=transactions,txnfilters&filterType=cash'))
            result = self.request_and_check(
                url, headers=JSON_HEADER,
                expected_content_type='text/json|application/json')
            data = json.loads(result.text)
            txns = data['set'][0].get('data', [])
            if not txns:
                break
            if start_date:
                last_dt = json_date_to_datetime(txns[-1]['odate'])
                if last_dt < start_date:
                    keep_txns = [
                        t for t in txns
                        if json_date_to_datetime(t['odate']) >= start_date]
                    all_txns.extend(keep_txns)
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
        df['odate'] = df['odate'].apply(json_date_to_datetime)

        if remove_pending:
            df = df[~df.isPending]
            df.reset_index(drop=True, inplace=True)

        df.amount = df.apply(reverse_credit_amount, axis=1)

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
            '{}/transactionDownload.event'.format(MINT_ROOT_URL) +
            ('?accountId=0' if include_investment else ''),
            expected_content_type='text/csv')
        return result.content

    def get_net_worth(self, account_data=None):
        if account_data is None:
            account_data = self.get_accounts()

        # account types in this list will be subtracted
        invert = set(['loan', 'loans', 'credit'])
        return sum([
            -a['currentBalance']
            if a['accountType'] in invert else a['currentBalance']
            for a in account_data if a['isActive']
        ])

    def get_transactions(self, include_investment=False):
        """Returns the transaction data as a Pandas DataFrame."""
        assert_pd()
        s = StringIO(self.get_transactions_csv(
            include_investment=include_investment))
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
            headers = dict(JSON_HEADER)
            headers['Referer'] = '{}/transaction.event?accountId={}'.format(
                MINT_ROOT_URL, account['id'])

            list_txn_url = '{}/listTransaction.xevent'.format(MINT_ROOT_URL)
            params = {
                'accountId': str(account['id']),
                'queryNew': '',
                'offset': 0,
                'comparableType': 8,
                'acctChanged': 'T',
                'rnd': Mint.get_rnd(),
            }

            response = json.loads(self.get(
                list_txn_url, params=params, headers=headers).text)
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
                account['availableMoney'] = parse_float(xml[1]['#text'])
                account['totalFees'] = parse_float(xml[3]['a']['#text'])
                if (account['interestRate'] is None):
                    account['interestRate'] = (
                        parse_float(xml[2]['#text']) / 100.0
                    )
            elif table_type == 'account-table-credit':
                account['availableMoney'] = parse_float(xml[1]['#text'])
                account['totalCredit'] = parse_float(xml[2]['#text'])
                account['totalFees'] = parse_float(xml[4]['a']['#text'])
                if account['interestRate'] is None:
                    account['interestRate'] = (
                        parse_float(xml[3]['#text']) / 100.0
                    )
            elif table_type == 'account-table-loan':
                account['nextPaymentAmount'] = (
                    parse_float(xml[1]['#text'])
                )
                account['nextPaymentDate'] = xml[2].get('#text', None)
            elif table_type == 'account-type-investment':
                account['totalFees'] = parse_float(xml[2]['a']['#text'])

        return accounts

    def get_categories(self):  # {{{
        # Get category metadata.
        req_id = self.get_request_id_str()
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

        cat_url = (
            '{}/bundledServiceController.xevent?legacy=false&token={}'.format(
                MINT_ROOT_URL, self.token))
        response = self.post(cat_url, data=data, headers=JSON_HEADER).text
        if req_id not in response:
            raise MintException('Could not parse category data: "' +
                                response + '"')
        response = json.loads(response)
        response = response['response'][req_id]['response']

        # Build category list
        categories = {}
        for category in response['allCategories']:
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
        url = "{}/getBudget.xevent".format(MINT_ROOT_URL)
        params = {
            'startDate': last_year,
            'endDate': this_month,
            'rnd': Mint.get_rnd(),
        }
        response = json.loads(self.get(url, params=params, headers=JSON_HEADER).text)

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
        self.post(
            '{}/refreshFILogins.xevent'.format(MINT_ROOT_URL),
            data={'token': self.token},
            headers=JSON_HEADER)


def get_accounts(email, password, get_detail=False):
    mint = Mint.create(email, password)
    return mint.get_accounts(get_detail=get_detail)


def get_net_worth(email, password):
    mint = Mint.create(email, password)
    account_data = mint.get_accounts()
    return mint.get_net_worth(account_data)


def make_accounts_presentable(accounts, presentable_format='EXCEL'):
    formatter = {
        'DATE': '%Y-%m-%d',
        'ISO8601': '%Y-%m-%dT%H:%M:%SZ',
        'EXCEL': '%Y-%m-%d %H:%M:%S',
    }[presentable_format]

    for account in accounts:
        for k, v in account.items():
            if isinstance(v, datetime):
                account[k] = v.strftime(formatter)
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
    cmdline.add_argument(
        'email',
        nargs='?',
        default=None,
        help='The e-mail address for your Mint.com account')
    cmdline.add_argument(
        'password',
        nargs='?',
        default=None,
        help='The password for your Mint.com account')

    cmdline.add_argument(
        '--accounts',
        action='store_true',
        dest='accounts',
        default=False,
        help='Retrieve account information'
        '(default if nothing else is specified)')
    cmdline.add_argument(
        '--budgets',
        action='store_true',
        dest='budgets',
        default=False,
        help='Retrieve budget information')
    cmdline.add_argument(
        '--net-worth',
        action='store_true',
        dest='net_worth',
        default=False,
        help='Retrieve net worth information')
    cmdline.add_argument(
        '--extended-accounts',
        action='store_true',
        dest='accounts_ext',
        default=False,
        help='Retrieve extended account information (slower, '
        'implies --accounts)')
    cmdline.add_argument(
        '--transactions',
        '-t',
        action='store_true',
        default=False,
        help='Retrieve transactions')
    cmdline.add_argument(
        '--extended-transactions',
        action='store_true',
        default=False,
        help='Retrieve transactions with extra information and arguments')
    cmdline.add_argument(
        '--start-date',
        nargs='?',
        default=None,
        help='Earliest date for transactions to be retrieved from. '
        'Used with --extended-transactions. Format: mm/dd/yy')
    cmdline.add_argument(
        '--include-investment',
        action='store_true',
        default=False,
        help='Used with --extended-transactions')
    cmdline.add_argument(
        '--skip-duplicates',
        action='store_true',
        default=False,
        help='Used with --extended-transactions')
    # Displayed to the user as a postive switch, but processed back
    # here as a negative
    cmdline.add_argument(
        '--show-pending',
        action='store_false',
        default=True,
        help='Exclude pending transactions from being retrieved. '
        'Used with --extended-transactions')
    cmdline.add_argument(
        '--filename', '-f',
        help='write results to file. can '
        'be {csv,json} format. default is to write to '
        'stdout.')
    cmdline.add_argument(
        '--keyring',
        action='store_true',
        help='Use OS keyring for storing password '
        'information')
    cmdline.add_argument(
        '--headless',
        action='store_true',
        help='Whether to execute chromedriver with no visible window.')
    cmdline.add_argument(
        '--mfa-method',
        default='sms',
        choices=['sms', 'email'],
        help='The MFA method to automate.')

    options = cmdline.parse_args()

    if options.keyring and not keyring:
        cmdline.error('--keyring can only be used if the `keyring` '
                      'library is installed.')

    try:  # python 2.x
        from __builtin__ import raw_input as input
    except ImportError:  # python 3
        from builtins import input
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
                options.extended_transactions, options.net_worth]):
        options.accounts = True

    mint = Mint.create(email, password,
                       mfa_method=options.mfa_method,
                       headless=options.headless)
    atexit.register(mint.close)  # Ensure everything is torn down.

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
        data = mint.get_transactions(
            include_investment=options.include_investment)
    elif options.extended_transactions:
        data = mint.get_detailed_transactions(
            start_date=options.start_date,
            include_investment=options.include_investment,
            remove_pending=options.show_pending,
            skip_duplicates=options.skip_duplicates)
    elif options.net_worth:
        data = mint.get_net_worth()

    # output the data
    if options.transactions or options.extended_transactions:
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

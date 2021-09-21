import atexit
from datetime import date, datetime, timedelta
import io
import json
import logging
import os
import os.path
import random
import re
import requests
import subprocess
from sys import platform as _platform
import time
import zipfile
import imaplib
import email
import email.header
import sys  # DEBUG
import warnings

try:
    from StringIO import StringIO  # Python 2
except ImportError:
    from io import BytesIO as StringIO  # Python 3

from selenium.common.exceptions import ElementNotInteractableException, ElementNotVisibleException, NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from seleniumrequests import Chrome
import xmltodict

try:
    import pandas as pd
except ImportError:
    pd = None

logger = logging.getLogger('mintapi')
logger.setLevel(logging.INFO)


def assert_pd():
    # Common function to check if pd is installed
    if not pd:
        raise ImportError(
            'transactions data requires pandas; '
            'please pip install pandas'
        )


def json_date_to_datetime(dateraw):
    cy = date.today().year
    try:
        newdate = datetime.strptime(dateraw + str(cy), '%b %d%Y')
    except ValueError:
        newdate = datetime.strptime(dateraw, '%m/%d/%y')
    return newdate


def reverse_credit_amount(row):
    amount = float(row['amount'][1:].replace(',', ''))
    return amount if row['isDebit'] else -amount


def get_email_code(imap_account, imap_password, imap_server, imap_folder, debug=False, delete=True):
    if debug:
        warnings.warn(
            "debug param to get_email_code() is deprecated and will be "
            "removed soon; use: logging.getLogger('mintapi')"
            ".setLevel(logging.DEBUG) to show DEBUG log messages.",
            DeprecationWarning)
    code = None
    imap_client = imaplib.IMAP4_SSL(imap_server)

    try:
        rv, data = imap_client.login(imap_account, imap_password)
    except imaplib.IMAP4.error:
        logger.error("ERROR: email login failed")
        return ''

    code = ''
    for c in range(20):
        time.sleep(10)
        rv, data = imap_client.select(imap_folder)
        if rv != 'OK':
            logger.error("ERROR: Unable to open mailbox ", rv)
            return ''

        rv, data = imap_client.search(None, "ALL")
        if rv != 'OK':
            logger.error("ERROR: Email search failed")
            return ''

        count = 0
        for num in data[0].split()[::-1]:
            count = count + 1
            if count > 3:
                break
            rv, data = imap_client.fetch(num, '(RFC822)')
            if rv != 'OK':
                logger.error("ERROR: ERROR getting message", num)
                sys.exit(1)

            msg = email.message_from_bytes(data[0][1])

            x = email.header.make_header(email.header.decode_header(msg['Subject']))
            subject = str(x)
            logger.debug("DEBUG: SUBJECT:", subject)

            x = email.header.make_header(email.header.decode_header(msg['From']))
            frm = str(x)
            logger.debug("DEBUG: FROM:", frm)

            if not re.search('do_not_reply@intuit.com', frm, re.IGNORECASE):
                continue

            if not re.search('Your Mint Account', subject, re.IGNORECASE):
                continue

            date_tuple = email.utils.parsedate_tz(msg['Date'])
            if date_tuple:
                local_date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
            else:
                logger.error("ERROR: FAIL0")

            diff = datetime.now() - local_date

            logger.debug("DEBUG: AGE:", diff.seconds)

            if diff.seconds > 180:
                continue

            logger.debug("DEBUG: EMAIL HEADER OK")

            body = str(msg)

            p = re.search(r'Verification code:<.*?(\d\d\d\d\d\d)$', body,
                          re.S | re.M)
            if p:
                code = p.group(1)
            else:
                logger.error("FAIL1")

            logger.debug("DEBUG: CODE FROM EMAIL:", code)

            if code != '':
                break

        logger.debug("DEBUG: CODE FROM EMAIL 2:", code)

        if code != '':
            logger.debug("DEBUG: CODE FROM EMAIL 3:", code)

            if delete and count > 0:
                imap_client.store(num, '+FLAGS', '\\Deleted')

            if delete:
                imap_client.expunge()

            break

    imap_client.logout()
    return code


CHROME_DRIVER_BASE_URL = 'https://chromedriver.storage.googleapis.com/'
CHROME_DRIVER_DOWNLOAD_PATH = '{version}/chromedriver_{arch}.zip'
CHROME_DRIVER_LATEST_RELEASE = 'LATEST_RELEASE'
CHROME_ZIP_TYPES = {
    'linux': 'linux64',
    'linux2': 'linux64',
    'darwin': 'mac64',
    'win32': 'win32',
    'win64': 'win32'
}
version_pattern = re.compile(
    "(?P<version>(?P<major>\\d+)\\.(?P<minor>\\d+)\\."
    "(?P<build>\\d+)\\.(?P<patch>\\d+))")


def get_chrome_driver_url(version, arch):
    return CHROME_DRIVER_BASE_URL + CHROME_DRIVER_DOWNLOAD_PATH.format(
        version=version, arch=CHROME_ZIP_TYPES.get(arch))


def get_chrome_driver_major_version_from_executable(local_executable_path):
    # Note; --version works on windows as well.
    # check_output fails if running from a thread without a console on win10.
    # To protect against this use explicit pipes for STDIN/STDERR.
    # See: https://github.com/pyinstaller/pyinstaller/issues/3392
    with open(os.devnull, 'wb') as devnull:
        version = subprocess.check_output(
            [local_executable_path, '--version'],
            stderr=devnull,
            stdin=devnull)
        version_match = version_pattern.search(version.decode())
        if not version_match:
            return None
        return version_match.groupdict()['major']


def get_latest_chrome_driver_version():
    """Returns the version of the latest stable chromedriver release."""
    latest_url = CHROME_DRIVER_BASE_URL + CHROME_DRIVER_LATEST_RELEASE
    latest_request = requests.get(latest_url)

    if latest_request.status_code != 200:
        raise RuntimeError(
            'Error finding the latest chromedriver at {}, status = {}'.format(
                latest_url, latest_request.status_code))
    return latest_request.text


def get_stable_chrome_driver(download_directory=os.getcwd()):
    chromedriver_name = 'chromedriver'
    if _platform in ['win32', 'win64']:
        chromedriver_name += '.exe'

    local_executable_path = os.path.join(download_directory, chromedriver_name)

    latest_chrome_driver_version = get_latest_chrome_driver_version()
    version_match = version_pattern.match(latest_chrome_driver_version)
    latest_major_version = None
    if not version_match:
        logger.error("Cannot parse latest chrome driver string: {}".format(
            latest_chrome_driver_version))
    else:
        latest_major_version = version_match.groupdict()['major']
    if os.path.exists(local_executable_path):
        major_version = get_chrome_driver_major_version_from_executable(
            local_executable_path)
        if major_version == latest_major_version or not latest_major_version:
            # Use the existing chrome driver, as it's already the latest
            # version or the latest version cannot be determined at the moment.
            return local_executable_path
        logger.info('Removing old version {} of Chromedriver'.format(
            major_version))
        os.remove(local_executable_path)

    if not latest_chrome_driver_version:
        logger.critical(
            'No local chrome driver found and cannot parse the latest chrome '
            'driver on the internet. Please double check your internet '
            'connection, then ask for assistance on the github project.')
        return None
    logger.info('Downloading version {} of Chromedriver'.format(
        latest_chrome_driver_version))
    zip_file_url = get_chrome_driver_url(
        latest_chrome_driver_version, _platform)
    request = requests.get(zip_file_url)

    if request.status_code != 200:
        raise RuntimeError(
            'Error finding chromedriver at {}, status = {}'.format(
                zip_file_url, request.status_code))

    zip_file = zipfile.ZipFile(io.BytesIO(request.content))
    zip_file.extractall(path=download_directory)
    os.chmod(local_executable_path, 0o755)
    return local_executable_path


def _create_web_driver_at_mint_com(headless=False, session_path=None, use_chromedriver_on_path=False, chromedriver_download_path=os.getcwd()):
    """
    Handles starting a web driver at mint.com
    """
    chrome_options = ChromeOptions()
    if headless:
        chrome_options.add_argument('headless')
        chrome_options.add_argument('no-sandbox')
        chrome_options.add_argument('disable-dev-shm-usage')
        chrome_options.add_argument('disable-gpu')
        # chrome_options.add_argument("--window-size=1920x1080")
    if session_path is not None:
        chrome_options.add_argument("user-data-dir=%s" % session_path)

    if use_chromedriver_on_path:
        driver = Chrome(options=chrome_options)
    else:
        driver = Chrome(
            options=chrome_options,
            executable_path=get_stable_chrome_driver(
                chromedriver_download_path))
    driver.get("https://www.mint.com")
    driver.implicitly_wait(20)  # seconds
    return driver


def _sign_in(email, password, driver, mfa_method=None, mfa_token=None,
             mfa_input_callback=None, intuit_account=None, wait_for_sync=True,
             wait_for_sync_timeout=5 * 60,
             imap_account=None, imap_password=None,
             imap_server=None, imap_folder="INBOX",
             ):
    """
    Takes in a web driver and gets it through the Mint sign in process
    """
    try:
        element = driver.find_element_by_link_text("Sign in")
    except NoSuchElementException:
        # when user has cookies, a slightly different front page appears
        driver.implicitly_wait(0)  # seconds
        element = driver.find_element_by_link_text("Sign in")
        driver.implicitly_wait(20)  # seconds
    element.click()
    time.sleep(1)
    try:  # try to enter in credentials if username and password are on same page
        email_input = driver.find_element_by_id("ius-userid")
        if not email_input.is_displayed():
            raise ElementNotVisibleException()
        email_input.clear()  # clear email and user specified email
        email_input.send_keys(email)
        driver.find_element_by_id("ius-password").send_keys(password)
        driver.find_element_by_id("ius-sign-in-submit-btn").submit()
    # try to enter in credentials if username and password are on different pages
    except (ElementNotInteractableException, ElementNotVisibleException):
        driver.implicitly_wait(0)
        try:
            email_input = driver.find_element_by_id("ius-identifier")
            if not email_input.is_displayed():
                raise ElementNotVisibleException()
            email_input.clear()  # clear email and use specified email
            email_input.send_keys(email)
            driver.find_element_by_id("ius-sign-in-submit-btn").click()
        # click on username if on the saved usernames page
        except (ElementNotInteractableException, ElementNotVisibleException):
            username_elements = driver.find_elements_by_class_name('ius-option-username')
            for username_element in username_elements:
                if username_element.text == email:
                    username_element.click()
                    break
        driver.implicitly_wait(5)
        try:
            driver.find_element_by_id(
                "ius-sign-in-mfa-password-collection-current-password").send_keys(password)
            driver.find_element_by_id(
                "ius-sign-in-mfa-password-collection-continue-btn").submit()
        except NoSuchElementException:
            pass  # password may not be here when using MFA

    # Wait until logged in, just in case we need to deal with MFA.
    while not driver.current_url.startswith(
            'https://mint.intuit.com/overview.event'):
        # An implicitly_wait is also necessary here to avoid getting stuck on
        # find_element_by_id while the page is still in transition.
        driver.implicitly_wait(1)
        time.sleep(1)

        # bypass "Let's add your current mobile number" interstitial page
        try:
            skip_for_now = driver.find_element_by_id('ius-verified-user-update-btn-skip')
            skip_for_now.click()
        except (NoSuchElementException, StaleElementReferenceException, ElementNotVisibleException):
            pass

        # mfa screen
        try:
            if mfa_method == 'soft-token':
                import oathtool
                mfa_token_input = driver.find_element_by_id('ius-mfa-soft-token')
                mfa_code = oathtool.generate_otp(mfa_token)
                mfa_token_input.send_keys(mfa_code)
                mfa_token_submit = driver.find_element_by_id('ius-mfa-soft-token-submit-btn')
                mfa_token_submit.click()
            else:
                try:
                    driver.find_element_by_id('ius-mfa-options-form')
                    mfa_method_option = driver.find_element_by_id(
                        'ius-mfa-option-{}'.format(mfa_method))
                    mfa_method_option.click()
                    mfa_method_submit = driver.find_element_by_id(
                        "ius-mfa-options-submit-btn")
                    mfa_method_submit.click()
                except NoSuchElementException:
                    pass  # no option to select mfa option

                if mfa_method == 'email' and imap_account:
                    for element_id in ["ius-mfa-email-otp-card-challenge", "ius-sublabel-mfa-email-otp"]:
                        try:
                            mfa_email_select = driver.find_element_by_id(element_id)
                            mfa_email_select.click()
                            break
                        except (NoSuchElementException, ElementNotInteractableException):
                            pass  # no option to select email address

                try:
                    mfa_code_input = driver.find_element_by_id("ius-mfa-confirm-code")
                    mfa_code_input.clear()
                    if mfa_method == 'email' and imap_account:
                        mfa_code = get_email_code(imap_account, imap_password, imap_server, imap_folder=imap_folder)
                    else:
                        mfa_code = (mfa_input_callback or input)("Please enter your 6-digit MFA code: ")
                    mfa_code_input.send_keys(mfa_code)

                    mfa_code_submit = driver.find_element_by_id("ius-mfa-otp-submit-btn")
                    mfa_code_submit.click()
                except (NoSuchElementException, ElementNotInteractableException):
                    pass  # we're not on mfa input screen

        except NoSuchElementException:
            pass  # not on mfa screen

        # account selection screen -- if there are multiple accounts, select one
        try:
            select_account = driver.find_element_by_id("ius-mfa-select-account-section")
            if intuit_account is not None:
                account_input = select_account.find_element_by_xpath(
                    "//label/span[text()='{}']/../preceding-sibling::input".format(intuit_account))
                account_input.click()
            driver.find_element_by_id("ius-sign-in-mfa-select-account-continue-btn").submit()
        except NoSuchElementException:
            pass  # not on account selection screen

        # password only sometimes after mfa
        try:
            driver.find_element_by_id("ius-sign-in-mfa-password-collection-current-password").send_keys(password)
            driver.find_element_by_id("ius-sign-in-mfa-password-collection-continue-btn").submit()
        except (NoSuchElementException, ElementNotInteractableException):
            pass  # not on secondary mfa password screen

        finally:
            driver.implicitly_wait(20)  # seconds


def get_web_driver(email, password, headless=False, mfa_method=None, mfa_token=None,
                   mfa_input_callback=None, intuit_account=None, wait_for_sync=True,
                   wait_for_sync_timeout=5 * 60,
                   session_path=None, imap_account=None, imap_password=None,
                   imap_server=None, imap_folder="INBOX",
                   use_chromedriver_on_path=False,
                   chromedriver_download_path=os.getcwd()):
    if headless and mfa_method is None:
        logger.warning("Using headless mode without specifying an MFA method "
                       "is unlikely to lead to a successful login. Defaulting "
                       "--mfa-method=sms")
        mfa_method = "sms"
    driver = _create_web_driver_at_mint_com(
        headless, session_path, use_chromedriver_on_path, chromedriver_download_path)

    status_message = None
    try:
        _sign_in(email, password, driver, mfa_method, mfa_token, mfa_input_callback, intuit_account, wait_for_sync, wait_for_sync_timeout, imap_account,
                 imap_password, imap_server, imap_folder)

        # Wait until the overview page has actually loaded, and if wait_for_sync==True, sync has completed.
        if wait_for_sync:
            try:
                # Status message might not be present straight away. Seems to be due
                # to dynamic content (client side rendering).
                status_message = WebDriverWait(driver, 30).until(
                    expected_conditions.visibility_of_element_located(
                        (By.CSS_SELECTOR, ".SummaryView .message")))
                WebDriverWait(driver, wait_for_sync_timeout).until(
                    lambda x: "Account refresh complete" in status_message.get_attribute('innerHTML')
                )
            except (TimeoutException, StaleElementReferenceException):
                logger.warning("Mint sync apparently incomplete after timeout. "
                               "Data retrieved may not be current.")
        else:
            driver.find_element_by_id("transaction")
    except Exception as e:
        logger.exception(e)
        driver.quit()
        driver = None

    if status_message is not None and isinstance(status_message, WebElement):
        status_message = status_message.text
    return driver, status_message


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
MINT_CREDIT_URL = 'https://credit.finance.intuit.com'

JSON_HEADER = {'accept': 'application/json'}


class MintException(Exception):
    pass


class Mint(object):
    request_id = 42  # magic number? random number?
    token = None
    driver = None
    status_message = None

    def __init__(self, email=None, password=None, mfa_method=None, mfa_token=None,
                 mfa_input_callback=None, intuit_account=None, headless=False, session_path=None,
                 imap_account=None, imap_password=None, imap_server=None,
                 imap_folder="INBOX", wait_for_sync=True, wait_for_sync_timeout=5 * 60,
                 use_chromedriver_on_path=False,
                 chromedriver_download_path=os.getcwd()):
        if email and password:
            self.login_and_get_token(email, password,
                                     mfa_method=mfa_method,
                                     mfa_token=mfa_token,
                                     mfa_input_callback=mfa_input_callback,
                                     intuit_account=intuit_account,
                                     headless=headless,
                                     session_path=session_path,
                                     imap_account=imap_account,
                                     imap_password=imap_password,
                                     imap_server=imap_server,
                                     imap_folder=imap_folder,
                                     wait_for_sync=wait_for_sync,
                                     wait_for_sync_timeout=wait_for_sync_timeout,
                                     use_chromedriver_on_path=use_chromedriver_on_path,
                                     chromedriver_download_path=chromedriver_download_path)

    @classmethod
    def create(cls, email, password, **opts):
        return Mint(email, password, **opts)

    @classmethod
    def get_rnd(cls):  # {{{
        return (str(int(time.mktime(datetime.now().timetuple()))) + str(
            random.randrange(999)).zfill(3))

    def _get_api_key_header(self):
        key_var = 'window.MintConfig.browserAuthAPIKey'
        api_key = self.driver.execute_script('return ' + key_var)
        auth = 'Intuit_APIKey intuit_apikey=' + api_key
        auth += ', intuit_apikey_version=1.0'
        header = {'authorization': auth}
        header.update(JSON_HEADER)
        return header

    def close(self):
        """Logs out and quits the current web driver/selenium session."""
        if not self.driver:
            return

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

    def login_and_get_token(self, email, password, mfa_method=None, mfa_token=None,
                            mfa_input_callback=None, intuit_account=None, headless=False,
                            session_path=None, imap_account=None,
                            imap_password=None,
                            imap_server=None,
                            imap_folder=None,
                            wait_for_sync=True,
                            wait_for_sync_timeout=5 * 60,
                            use_chromedriver_on_path=False,
                            chromedriver_download_path=os.getcwd()):
        if self.token and self.driver:
            return

        self.driver, self.status_message = get_web_driver(
            email, password,
            mfa_method=mfa_method,
            mfa_token=mfa_token,
            mfa_input_callback=mfa_input_callback,
            intuit_account=intuit_account,
            headless=headless,
            session_path=session_path,
            imap_account=imap_account,
            imap_password=imap_password,
            imap_server=imap_server,
            imap_folder=imap_folder,
            wait_for_sync=wait_for_sync,
            wait_for_sync_timeout=wait_for_sync_timeout,
            use_chromedriver_on_path=use_chromedriver_on_path,
            chromedriver_download_path=chromedriver_download_path)
        if self.driver is not None:  # check if sign in failed
            self.token = self.get_token()

    def get_token(self):
        value_json = self.driver.find_element_by_name(
            'javascript-user').get_attribute('value')
        return json.loads(value_json)['token']

    def get_request_id_str(self):
        req_id = self.request_id
        self.request_id += 1
        return str(req_id)

    def get_attention(self):
        attention = None
        # noinspection PyBroadException
        try:
            if "complete" in self.status_message:
                attention = self.status_message.split(".")[1].strip()
            else:
                attention = self.status_message
        except Exception:
            pass
        return attention

    def get_bills(self):
        return self.get(
            '{}/bps/v2/payer/bills'.format(MINT_ROOT_URL),
            headers=self._get_api_key_header()
        ).json()['bills']

    def get_invests_json(self):
        body = self.get(
            '{}/investment.event'.format(MINT_ROOT_URL),
        ).text
        p = re.search(r'<input name="json-import-node" type="hidden" value="json = ([^"]*);"', body)
        if p:
            return p.group(1).replace('&quot;', '"')
        else:
            logger.error("FAIL2")

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
                              skip_duplicates=False, start_date=None, id=0):
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
        except (TypeError, ValueError):
            start_date = None
        all_txns = []
        offset = 0
        # Mint only returns some of the transactions at once.  To get all of
        # them, we have to keep asking for more until we reach the end.
        while 1:
            url = MINT_ROOT_URL + '/getJsonData.xevent'
            params = {
                'queryNew': '',
                'offset': offset,
                'comparableType': '8',
                'rnd': Mint.get_rnd(),
            }
            # Specifying accountId=0 causes Mint to return investment
            # transactions as well.  Otherwise they are skipped by
            # default.
            if id > 0 or include_investment:
                params['accountId'] = id
            if include_investment:
                params['task'] = 'transactions'
            else:
                params['task'] = 'transactions,txnfilters'
                params['filterType'] = 'cash'
            result = self.request_and_check(
                url, headers=JSON_HEADER, params=params,
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

    def get_transactions_csv(self, include_investment=False, acct=0):
        """Returns the raw CSV transaction data as downloaded from Mint.

        If include_investment == True, also includes transactions that Mint
        classifies as investment-related.  You may find that the investment
        transaction data is not sufficiently detailed to actually be useful,
        however.
        """

        # Specifying accountId=0 causes Mint to return investment
        # transactions as well.  Otherwise they are skipped by
        # default.
        params = None
        if include_investment or acct > 0:
            params = {'accountId': acct}
        result = self.request_and_check(
            '{}/transactionDownload.event'.format(MINT_ROOT_URL),
            params=params,
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
                       .replace('uncategorized', pd.NA))
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
            raise MintException(
                'Could not parse category data: "{}"'.format(response))
        response = json.loads(response)
        response = response['response'][req_id]['response']

        # Build category list
        categories = {}
        for category in response['allCategories']:
            categories[category['id']] = category

        return categories

    def get_budgets(self, hist=None):  # {{{
        # Get categories
        categories = self.get_categories()

        # Issue request for budget utilization
        first_of_this_month = date.today().replace(day=1)
        eleven_months_ago = (first_of_this_month - timedelta(days=330)).replace(day=1)
        url = "{}/getBudget.xevent".format(MINT_ROOT_URL)
        params = {
            'startDate': eleven_months_ago.strftime('%m/%d/%Y'),
            'endDate': first_of_this_month.strftime('%m/%d/%Y'),
            'rnd': Mint.get_rnd(),
        }
        response = json.loads(self.get(url, params=params, headers=JSON_HEADER).text)

        if hist is not None:  # version proofing api
            def mos_to_yrmo(mos_frm_zero):
                return datetime(year=int(mos_frm_zero / 12),
                                month=mos_frm_zero % 12 + 1,
                                day=1).strftime("%Y%m")

            # Error checking 'hist' argument
            if isinstance(hist, str) or hist > 12:
                hist = 12  # MINT_ROOT_URL only calls last 12 months of budget data
            elif hist < 1:
                hist = 1

            bgt_cur_mo = max(map(int, response['data']['income'].keys()))
            min_mo_hist = bgt_cur_mo - hist

            # Initialize and populate dictionary for return
            #   Output 'budgets' dictionary with structure
            #       { "YYYYMM": {"spending": [{"key": value, ...}, ...],
            #                      "income": [{"key": value, ...}, ...] } }
            budgets = {}
            for months in range(bgt_cur_mo, min_mo_hist, -1):
                budgets[mos_to_yrmo(months)] = {}
                budgets[mos_to_yrmo(months)][
                    "income"] = response["data"]["income"][str(months)]['bu']
                budgets[mos_to_yrmo(months)][
                    "spending"] = response["data"]["spending"][str(months)]['bu']

            # Fill in the return structure
            for month in budgets.keys():
                for direction in budgets[month]:
                    for budget in budgets[month][direction]:
                        category = self.get_category_object_from_id(budget['cat'], categories)
                        budget['cat'] = category['name']
                        budget['parent'] = category['parent']['name']

        else:
            # Make the skeleton return structure
            budgets = {
                'income': response['data']['income'][
                    str(max(map(int, response['data']['income'].keys())))
                ]['bu'],
                'spend': response['data']['spending'][
                    str(max(map(int, response['data']['spending'].keys())))
                ]['bu']
            }

            # Fill in the return structure
            for direction in budgets.keys():
                for budget in budgets[direction]:
                    category = self.get_category_object_from_id(budget['cat'], categories)
                    budget['cat'] = category['name']
                    # Uncategorized budget's parent is a string: 'Uncategorized'
                    if isinstance(category['parent'], dict):
                        budget['parent'] = category['parent']['name']
                    else:
                        budget['parent'] = category['parent']

        return budgets

    def get_category_from_id(self, cid, categories):
        category = self.get_category_object_from_id(cid, categories)
        return category['name']

    def get_category_object_from_id(self, cid, categories):
        if cid == 0:
            return {'parent': 'Uncategorized', 'name': 'Uncategorized'}

        for i in categories:
            if categories[i]['id'] == cid:
                return categories[i]

            if 'children' in categories[i]:
                for j in categories[i]['children']:
                    if categories[i][j]['id'] == cid:
                        return categories[i][j]

        return {'parent': 'Unknown', 'name': 'Unknown'}

    def initiate_account_refresh(self):
        self.post(
            '{}/refreshFILogins.xevent'.format(MINT_ROOT_URL),
            data={'token': self.token},
            headers=JSON_HEADER)

    def get_credit_score(self):
        # Request a single credit report, and extract the score
        report = self.get_credit_report(limit=1, details=False)
        try:
            vendor = report['reports']['vendorReports'][0]
            return vendor['creditReportList'][0]['creditScore']
        except (KeyError, IndexError):
            raise Exception('No Credit Score Found')

    def get_credit_report(self, limit=2, details=True):
        # Get the browser API key, build auth header
        credit_header = self._get_api_key_header()

        # Get credit reports. The UI shows 2 by default, but more are available!
        # At least 8, but could be all the TransUnion reports Mint has
        # How the "bands" are defined, and other metadata, is available at a
        # /v1/creditscoreproviders/3 endpoint (3 = TransUnion)
        credit_report = dict()
        response = self.get(
            '{}/v1/creditreports?limit={}'.format(MINT_CREDIT_URL, limit),
            headers=credit_header)
        credit_report['reports'] = response.json()

        # If we want details, request the detailed sub-reports
        if details:
            # Get full list of credit inquiries
            response = self.get(
                '{}/v1/creditreports/0/inquiries'.format(MINT_CREDIT_URL),
                headers=credit_header)
            credit_report['inquiries'] = response.json()

            # Get full list of credit accounts
            response = self.get(
                '{}/v1/creditreports/0/tradelines'.format(MINT_CREDIT_URL),
                headers=credit_header)
            credit_report['accounts'] = response.json()

            # Get credit utilization history (~3 months, by account)
            response = self.get(
                '{}/v1/creditreports/creditutilizationhistory'.format(MINT_CREDIT_URL),
                headers=credit_header)
            clean_data = self.process_utilization(response.json())
            credit_report['utilization'] = clean_data

        return credit_report

    def process_utilization(self, data):
        # Function to clean up the credit utilization history data
        utilization = []
        utilization.extend(self.flatten_utilization(data['cumulative']))
        for trade in data['tradelines']:
            utilization.extend(self.flatten_utilization(trade))
        return utilization

    def flatten_utilization(self, data):
        # The utilization history data has a nested format, grouped by year
        # and then by month. Let's flatten that into a list of dates.
        utilization = []
        name = data.get('creditorName', 'Total')
        for cu in data['creditUtilization']:
            year = cu['year']
            for cu_month in cu['months']:
                date = datetime.strptime(cu_month['name'], '%B').replace(
                    day=1, year=int(year))
                utilization.append({
                    'name': name,
                    'date': date.strftime('%Y-%m-%d'),
                    'utilization': cu_month['creditUtilization']
                })
        return utilization


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


def get_credit_score(email, password):
    mint = Mint.create(email, password)
    return mint.get_credit_score()


def get_credit_report(email, password):
    mint = Mint.create(email, password)
    return mint.get_credit_report()


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

    home = os.path.expanduser("~")
    default_session_path = os.path.join(home, '.mintapi', 'session')
    cmdline.add_argument(
        '--session-path',
        nargs='?',
        default=default_session_path,
        help='Directory to save browser session, including cookies. '
        'Used to prevent repeated MFA prompts. Defaults to '
        '$HOME/.mintapi/session.  Set to None to use '
        'a temporary profile.')
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
        '--budget_hist',
        action='store_true',
        dest='budget_hist',
        default=None,
        help='Retrieve 12-month budget history information')
    cmdline.add_argument(
        '--net-worth',
        action='store_true',
        dest='net_worth',
        default=False,
        help='Retrieve net worth information')
    cmdline.add_argument(
        '--credit-score',
        action='store_true',
        dest='credit_score',
        default=False,
        help='Retrieve current credit score')
    cmdline.add_argument(
        '--credit-report',
        action='store_true',
        dest='credit_report',
        default=False,
        help='Retrieve full credit report')
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
        '--use-chromedriver-on-path',
        action='store_true',
        help=('Whether to use the chromedriver on PATH, instead of '
              'downloading a local copy.'))
    cmdline.add_argument(
        '--chromedriver-download-path',
        default=os.getcwd(),
        help=('The directory to download chromedrive to.'))
    cmdline.add_argument(
        '--mfa-method',
        default='sms',
        choices=['sms', 'email', 'soft-token'],
        help='The MFA method to automate.')
    cmdline.add_argument(
        '--mfa-token',
        default=None,
        help='The MFA soft-token to pass to oathtool.')
    cmdline.add_argument(
        '--imap-account',
        default=None,
        help='IMAP login account')
    cmdline.add_argument(
        '--imap-password',
        default=None,
        help='IMAP login password')
    cmdline.add_argument(
        '--imap-server',
        default=None,
        help='IMAP server')
    cmdline.add_argument(
        '--imap-folder',
        default="INBOX",
        help='IMAP folder')
    cmdline.add_argument(
        '--imap-test',
        action='store_true',
        help='Test imap login and retrieval.')
    cmdline.add_argument(
        '--no_wait_for_sync',
        action='store_true',
        default=False,
        help=('By default, mint api will wait for accounts to sync with the '
              'backing financial institutions. If this flag is present, do '
              'not wait for them to sync.'))
    cmdline.add_argument(
        '--wait_for_sync_timeout',
        type=int,
        default=5 * 60,
        help=('Number of seconds to wait for sync.  Default is 5 minutes'))
    cmdline.add_argument(
        '--attention',
        action='store_true',
        help='Display accounts that need attention (None if none).')

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
                options.extended_transactions, options.net_worth, options.credit_score,
                options.credit_report, options.attention]):
        options.accounts = True

    if options.session_path == 'None':
        session_path = None
    else:
        session_path = options.session_path

    mint = Mint.create(
        email, password,
        mfa_method=options.mfa_method,
        mfa_token=options.mfa_token,
        session_path=session_path,
        headless=options.headless,
        imap_account=options.imap_account,
        imap_password=options.imap_password,
        imap_server=options.imap_server,
        imap_folder=options.imap_folder,
        wait_for_sync=not options.no_wait_for_sync,
        wait_for_sync_timeout=options.wait_for_sync_timeout,
        use_chromedriver_on_path=options.use_chromedriver_on_path,
        chromedriver_download_path=options.chromedriver_download_path
    )
    atexit.register(mint.close)  # Ensure everything is torn down.

    if options.imap_test:
        mfa_code = get_email_code(
            options.imap_account, options.imap_password, options.imap_server,
            imap_folder=options.imap_folder, delete=False)
        print("MFA CODE:", mfa_code)
        sys.exit()

    data = None
    if options.accounts and options.budgets:
        try:
            accounts = make_accounts_presentable(
                mint.get_accounts(get_detail=options.accounts_ext)
            )
        except Exception:
            accounts = None

        try:
            budgets = mint.get_budgets()
        except Exception:
            budgets = None

        data = {'accounts': accounts, 'budgets': budgets}
    elif options.budgets:
        try:
            data = mint.get_budgets()
        except Exception:
            data = None
    elif options.budget_hist:
        try:
            data = mint.get_budgets(hist=12)
        except Exception:
            data = None
    elif options.accounts:
        try:
            data = make_accounts_presentable(mint.get_accounts(
                get_detail=options.accounts_ext)
            )
        except Exception:
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
    elif options.credit_score:
        data = mint.get_credit_score()
    elif options.credit_report:
        data = mint.get_credit_report(details=True)

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

    if options.attention:
        attention_msg = mint.get_attention()
        if attention_msg is None or attention_msg == "":
            attention_msg = "no messages"
        if options.filename is None:
            print(attention_msg)
        else:
            with open(options.filename, 'w+') as f:
                f.write(attention_msg)


if __name__ == '__main__':
    main()

from datetime import datetime
import email
import email.header
import imaplib
import json
import io
import logging
import os
import re
import requests
import subprocess
import sys
import time
import zipfile
import warnings

from selenium.common.exceptions import (
    ElementNotInteractableException,
    ElementNotVisibleException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from seleniumrequests import Chrome

import oathtool

logger = logging.getLogger("mintapi")


def get_email_code(
    imap_account, imap_password, imap_server, imap_folder, debug=False, delete=True
):
    if debug:
        warnings.warn(
            "debug param to get_email_code() is deprecated and will be "
            "removed soon; use: logging.getLogger('mintapi')"
            ".setLevel(logging.DEBUG) to show DEBUG log messages.",
            DeprecationWarning,
        )
    code = None
    try:
        imap_client = imaplib.IMAP4_SSL(imap_server)
    except imaplib.IMAP4.error:
        logger.error("ERROR: Unable to establish IMAP Client")
        return ""

    try:
        rv, data = imap_client.login(imap_account, imap_password)
    except imaplib.IMAP4.error:
        logger.error("ERROR: email login failed")
        return ""

    code = ""
    for c in range(20):
        time.sleep(10)
        rv, data = imap_client.select(imap_folder)
        if rv != "OK":
            logger.error("ERROR: Unable to open mailbox ", rv)
            return ""

        rv, data = imap_client.search(None, "ALL")
        if rv != "OK":
            logger.error("ERROR: Email search failed")
            return ""

        count = 0
        for num in data[0].split()[::-1]:
            count = count + 1
            if count > 3:
                break
            rv, data = imap_client.fetch(num, "(RFC822)")
            if rv != "OK":
                logger.error("ERROR: ERROR getting message", num)
                sys.exit(1)

            msg = email.message_from_bytes(data[0][1])

            x = email.header.make_header(email.header.decode_header(msg["Subject"]))
            subject = str(x)
            logger.debug("DEBUG: SUBJECT:", subject)

            x = email.header.make_header(email.header.decode_header(msg["From"]))
            frm = str(x)
            logger.debug("DEBUG: FROM:", frm)

            if not re.search("do_not_reply@intuit.com", frm, re.IGNORECASE):
                continue

            if not re.search("Your Mint Account", subject, re.IGNORECASE):
                continue

            date_tuple = email.utils.parsedate_tz(msg["Date"])
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

            p = re.search(r"Verification code:<.*?(\d\d\d\d\d\d)$", body, re.S | re.M)
            if p:
                code = p.group(1)
            else:
                logger.error("FAIL1")

            logger.debug("DEBUG: CODE FROM EMAIL:", code)

            if code != "":
                break

        logger.debug("DEBUG: CODE FROM EMAIL 2:", code)

        if code != "":
            logger.debug("DEBUG: CODE FROM EMAIL 3:", code)

            if delete and count > 0:
                imap_client.store(num, "+FLAGS", "\\Deleted")

            if delete:
                imap_client.expunge()

            break

    imap_client.logout()
    return code


CHROME_DRIVER_BASE_URL = "https://chromedriver.storage.googleapis.com/"
CHROME_DRIVER_DOWNLOAD_PATH = "{version}/chromedriver_{arch}.zip"
CHROME_DRIVER_LATEST_RELEASE = "LATEST_RELEASE"
CHROME_ZIP_TYPES = {
    "linux": "linux64",
    "linux2": "linux64",
    "darwin": "mac64",
    "win32": "win32",
    "win64": "win32",
}
version_pattern = re.compile(
    "(?P<version>(?P<major>\\d+)\\.(?P<minor>\\d+)\\."
    "(?P<build>\\d+)\\.(?P<patch>\\d+))"
)


def get_chrome_driver_url(version, arch):
    return CHROME_DRIVER_BASE_URL + CHROME_DRIVER_DOWNLOAD_PATH.format(
        version=version, arch=CHROME_ZIP_TYPES.get(arch)
    )


def get_chrome_driver_major_version_from_executable(local_executable_path):
    # Note; --version works on windows as well.
    # check_output fails if running from a thread without a console on win10.
    # To protect against this use explicit pipes for STDIN/STDERR.
    # See: https://github.com/pyinstaller/pyinstaller/issues/3392
    with open(os.devnull, "wb") as devnull:
        version = subprocess.check_output(
            [local_executable_path, "--version"], stderr=devnull, stdin=devnull
        )
        version_match = version_pattern.search(version.decode())
        if not version_match:
            return None
        return version_match.groupdict()["major"]


def get_latest_chrome_driver_version():
    """Returns the version of the latest stable chromedriver release."""
    latest_url = CHROME_DRIVER_BASE_URL + CHROME_DRIVER_LATEST_RELEASE
    latest_request = requests.get(latest_url)

    if latest_request.status_code != 200:
        raise RuntimeError(
            "Error finding the latest chromedriver at {}, status = {}".format(
                latest_url, latest_request.status_code
            )
        )
    return latest_request.text


def get_stable_chrome_driver(download_directory=os.getcwd()):
    chromedriver_name = "chromedriver"
    if sys.platform in ["win32", "win64"]:
        chromedriver_name += ".exe"

    local_executable_path = os.path.join(download_directory, chromedriver_name)

    latest_chrome_driver_version = get_latest_chrome_driver_version()
    version_match = version_pattern.match(latest_chrome_driver_version)
    latest_major_version = None
    if not version_match:
        logger.error(
            "Cannot parse latest chrome driver string: {}".format(
                latest_chrome_driver_version
            )
        )
    else:
        latest_major_version = version_match.groupdict()["major"]
    if os.path.exists(local_executable_path):
        major_version = get_chrome_driver_major_version_from_executable(
            local_executable_path
        )
        if major_version == latest_major_version or not latest_major_version:
            # Use the existing chrome driver, as it's already the latest
            # version or the latest version cannot be determined at the moment.
            return local_executable_path
        logger.info("Removing old version {} of Chromedriver".format(major_version))
        os.remove(local_executable_path)

    if not latest_chrome_driver_version:
        logger.critical(
            "No local chrome driver found and cannot parse the latest chrome "
            "driver on the internet. Please double check your internet "
            "connection, then ask for assistance on the github project."
        )
        return None
    logger.info(
        "Downloading version {} of Chromedriver".format(latest_chrome_driver_version)
    )
    zip_file_url = get_chrome_driver_url(latest_chrome_driver_version, sys.platform)
    request = requests.get(zip_file_url)

    if request.status_code != 200:
        raise RuntimeError(
            "Error finding chromedriver at {}, status = {}".format(
                zip_file_url, request.status_code
            )
        )

    zip_file = zipfile.ZipFile(io.BytesIO(request.content))
    zip_file.extractall(path=download_directory)
    os.chmod(local_executable_path, 0o755)
    return local_executable_path


def _create_web_driver_at_mint_com(
    headless=False,
    session_path=None,
    use_chromedriver_on_path=False,
    chromedriver_download_path=os.getcwd(),
):
    """
    Handles starting a web driver at mint.com
    """
    chrome_options = ChromeOptions()
    if headless:
        chrome_options.add_argument("headless")
        chrome_options.add_argument("no-sandbox")
        chrome_options.add_argument("disable-dev-shm-usage")
        chrome_options.add_argument("disable-gpu")
        # chrome_options.add_argument("--window-size=1920x1080")
    if session_path is not None:
        chrome_options.add_argument("user-data-dir=%s" % session_path)

    if use_chromedriver_on_path:
        driver = Chrome(options=chrome_options)
    else:
        driver = Chrome(
            options=chrome_options,
            executable_path=get_stable_chrome_driver(chromedriver_download_path),
        )
    return driver


def get_token(driver: Chrome):
    value_json = driver.find_element_by_name("javascript-user").get_attribute("value")
    return json.loads(value_json)["token"]


def sign_in(
    email,
    password,
    driver,
    mfa_method=None,
    mfa_token=None,
    mfa_input_callback=None,
    intuit_account=None,
    wait_for_sync=True,
    wait_for_sync_timeout=5 * 60,
    imap_account=None,
    imap_password=None,
    imap_server=None,
    imap_folder="INBOX",
):
    """
    Takes in a web driver and gets it through the Mint sign in process
    """
    driver.implicitly_wait(20)  # seconds
    driver.get("https://www.mint.com")
    element = driver.find_element_by_link_text("Sign in")
    element.click()

    WebDriverWait(driver, 20).until(
        expected_conditions.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                "#ius-link-use-a-different-id-known-device, #ius-userid, #ius-identifier, #ius-option-username",
            )
        )
    )
    driver.implicitly_wait(0)  # seconds

    # click "Use a different user ID" if needed
    try:
        driver.find_element_by_id("ius-link-use-a-different-id-known-device").click()
        WebDriverWait(driver, 20).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, "#ius-userid, #ius-identifier, #ius-option-username")
            )
        )
    except NoSuchElementException:
        pass

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
        try:
            email_input = driver.find_element_by_id("ius-identifier")
            if not email_input.is_displayed():
                raise ElementNotVisibleException()
            email_input.clear()  # clear email and use specified email
            email_input.send_keys(email)
            driver.find_element_by_id("ius-sign-in-submit-btn").click()
        # click on username if on the saved usernames page
        except (ElementNotInteractableException, ElementNotVisibleException):
            username_elements = driver.find_elements_by_class_name(
                "ius-option-username"
            )
            for username_element in username_elements:
                if username_element.text == email:
                    username_element.click()
                    break
        driver.implicitly_wait(20)  # seconds
        try:
            driver.find_element_by_id(
                "ius-sign-in-mfa-password-collection-current-password"
            ).send_keys(password)
            driver.find_element_by_id(
                "ius-sign-in-mfa-password-collection-continue-btn"
            ).submit()
        except NoSuchElementException:
            pass  # password may not be here when using MFA

    # Wait until logged in, just in case we need to deal with MFA.
    driver.implicitly_wait(1)  # seconds
    while not driver.current_url.startswith("https://mint.intuit.com/overview.event"):

        # bypass "Let's add your current mobile number" interstitial page
        try:
            skip_for_now = driver.find_element_by_id(
                "ius-verified-user-update-btn-skip"
            )
            skip_for_now.click()
        except (
            NoSuchElementException,
            StaleElementReferenceException,
            ElementNotVisibleException,
        ):
            pass

        # mfa screen
        try:
            if mfa_method == "soft-token":
                mfa_token_input = driver.find_element_by_css_selector(
                    "#iux-mfa-soft-token-verification-code, #ius-mfa-soft-token"
                )
                if mfa_input_callback is not None:
                    mfa_code = mfa_input_callback(
                        "Please enter your 6-digit MFA code: "
                    )
                else:
                    mfa_code = oathtool.generate_otp(mfa_token)
                mfa_token_input.send_keys(mfa_code)
                mfa_token_submit = driver.find_element_by_css_selector(
                    '#ius-mfa-soft-token-submit-btn, [data-testid="VerifySoftTokenSubmitButton"]'
                )
                mfa_token_submit.click()
            else:
                try:
                    driver.find_element_by_id("ius-mfa-options-form")
                    mfa_method_option = driver.find_element_by_id(
                        "ius-mfa-option-{}".format(mfa_method)
                    )
                    mfa_method_option.click()
                    mfa_method_submit = driver.find_element_by_id(
                        "ius-mfa-options-submit-btn"
                    )
                    mfa_method_submit.click()
                except NoSuchElementException:
                    pass  # no option to select mfa option

                if mfa_method == "email" and imap_account:
                    for element_id in [
                        "ius-label-mfa-email-otp",
                        "ius-mfa-email-otp-card-challenge",
                        "ius-sublabel-mfa-email-otp",
                    ]:
                        try:
                            mfa_email_select = driver.find_element_by_id(element_id)
                            mfa_email_select.click()
                            break
                        except (
                            NoSuchElementException,
                            ElementNotInteractableException,
                        ):
                            pass  # no option to select email address

                if mfa_method == "sms":
                    try:
                        mfa_sms_select = driver.find_element_by_id(
                            "ius-mfa-sms-otp-card-challenge"
                        )
                        mfa_sms_select.click()
                    except (NoSuchElementException, ElementNotInteractableException):
                        pass  # no option to select sms

                try:
                    mfa_code_input = driver.find_element_by_id("ius-mfa-confirm-code")
                    mfa_code_input.clear()
                    if mfa_method == "email" and imap_account:
                        mfa_code = get_email_code(
                            imap_account,
                            imap_password,
                            imap_server,
                            imap_folder=imap_folder,
                        )
                    else:
                        mfa_code = (mfa_input_callback or input)(
                            "Please enter your 6-digit MFA code: "
                        )
                    mfa_code_input.send_keys(mfa_code)

                    mfa_code_submit = driver.find_element_by_css_selector(
                        '#ius-mfa-otp-submit-btn, [data-testid="VerifyOtpSubmitButton"]'
                    )
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
                    "//label/span[text()='{}']/../preceding-sibling::input".format(
                        intuit_account
                    )
                )
                account_input.click()

            mfa_code_submit = driver.find_element_by_css_selector(
                '#ius-sign-in-mfa-select-account-continue-btn, [data-testid="SelectAccountContinueButton"]'
            )
            mfa_code_submit.click()
        except NoSuchElementException:
            pass  # not on account selection screen

        # password only sometimes after mfa
        try:
            driver.find_element_by_id(
                "ius-sign-in-mfa-password-collection-current-password"
            ).send_keys(password)
            driver.find_element_by_id(
                "ius-sign-in-mfa-password-collection-continue-btn"
            ).submit()
        except (NoSuchElementException, ElementNotInteractableException):
            pass  # not on secondary mfa password screen
    driver.implicitly_wait(20)  # seconds

    # Wait until the overview page has actually loaded, and if wait_for_sync==True, sync has completed.
    status_message = None
    if wait_for_sync:
        try:
            # Status message might not be present straight away. Seems to be due
            # to dynamic content (client side rendering).
            status_web_element = WebDriverWait(driver, 30).until(
                expected_conditions.visibility_of_element_located(
                    (By.CSS_SELECTOR, ".SummaryView .message")
                )
            )
            WebDriverWait(driver, wait_for_sync_timeout).until(
                lambda x: "Account refresh complete"
                in status_web_element.get_attribute("innerHTML")
            )
            status_message = status_web_element.text
        except (TimeoutException, StaleElementReferenceException):
            logger.warning(
                "Mint sync apparently incomplete after timeout. "
                "Data retrieved may not be current."
            )
    return status_message, get_token(driver)


def get_web_driver(
    email,
    password,
    headless=False,
    mfa_method=None,
    mfa_token=None,
    mfa_input_callback=None,
    intuit_account=None,
    wait_for_sync=True,
    wait_for_sync_timeout=5 * 60,
    session_path=None,
    imap_account=None,
    imap_password=None,
    imap_server=None,
    imap_folder="INBOX",
    use_chromedriver_on_path=False,
    chromedriver_download_path=os.getcwd(),
):
    warnings.warn(
        "get_web_driver instance function is going to be deprecated in the next major release"
        "please use login_and_get_token or sign_in",
        DeprecationWarning,
    )
    if headless and mfa_method is None:
        logger.warning(
            "Using headless mode without specifying an MFA method "
            "is unlikely to lead to a successful login. Defaulting "
            "--mfa-method=sms"
        )
        mfa_method = "sms"
    driver = _create_web_driver_at_mint_com(
        headless, session_path, use_chromedriver_on_path, chromedriver_download_path
    )

    status_message = None
    try:
        status_message, _ = sign_in(
            email,
            password,
            driver,
            mfa_method,
            mfa_token,
            mfa_input_callback,
            intuit_account,
            wait_for_sync,
            wait_for_sync_timeout,
            imap_account,
            imap_password,
            imap_server,
            imap_folder,
        )
    except Exception as e:
        logger.exception(e)
        driver.quit()
        driver = None

    return driver, status_message

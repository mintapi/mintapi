from datetime import datetime
from mintapi import constants, exceptions
import email
import email.header
import imaplib
import io
import logging
import os
import re
import requests
import subprocess
import sys
import time
import zipfile
import itertools

from selenium.common.exceptions import (
    ElementNotInteractableException,
    ElementNotVisibleException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from seleniumrequests import Chrome

import oathtool

logger = logging.getLogger("mintapi")


class MFAMethodNotAvailableError(RuntimeError):
    pass


SELECT_CSS_SELECTORS_LABEL = "select_css_selectors"
INPUT_CSS_SELECTORS_LABEL = "input_css_selectors"
SPAN_CSS_SELECTORS_LABEL = "span_css_selectors"
BUTTON_CSS_SELECTORS_LABEL = "button_css_selectors"

MFA_METHODS = [
    {
        constants.MFA_METHOD_LABEL: constants.MFA_VIA_SOFT_TOKEN,
        SELECT_CSS_SELECTORS_LABEL: '#iux-mfa-soft-token-verification-code, #ius-mfa-soft-token, [data-testid="VerifySoftTokenInput"]',
        INPUT_CSS_SELECTORS_LABEL: '#iux-mfa-soft-token-verification-code, #ius-mfa-soft-token, [data-testid="VerifySoftTokenInput"]',
        SPAN_CSS_SELECTORS_LABEL: "",
        BUTTON_CSS_SELECTORS_LABEL: '#ius-mfa-soft-token-submit-btn, [data-testid="VerifySoftTokenSubmitButton"]',
    },
    {
        constants.MFA_METHOD_LABEL: constants.MFA_VIA_AUTHENTICATOR,
        SELECT_CSS_SELECTORS_LABEL: '#iux-mfa-soft-token-verification-code, #ius-mfa-soft-token, [data-testid="VerifySoftTokenInput"]',
        INPUT_CSS_SELECTORS_LABEL: '#iux-mfa-soft-token-verification-code, #ius-mfa-soft-token, [data-testid="VerifySoftTokenInput"]',
        SPAN_CSS_SELECTORS_LABEL: '[data-testid="VerifySoftTokenSubHeader"]',
        BUTTON_CSS_SELECTORS_LABEL: '#ius-mfa-soft-token-submit-btn, [data-testid="VerifySoftTokenSubmitButton"]',
    },
    {
        constants.MFA_METHOD_LABEL: constants.MFA_VIA_EMAIL,
        SELECT_CSS_SELECTORS_LABEL: '#ius-label-mfa-email-otp, #ius-mfa-email-otp-card-challenge, #ius-sublabel-mfa-email-otp, [data-testid="challengePickerOption_EMAIL_OTP"]',
        INPUT_CSS_SELECTORS_LABEL: "#ius-mfa-confirm-code",
        SPAN_CSS_SELECTORS_LABEL: '[data-testid="VerifyOtpHeaderText"], #VerifyOtpHeader',
        BUTTON_CSS_SELECTORS_LABEL: '#ius-mfa-otp-submit-btn, [data-testid="VerifyOtpSubmitButton"]',
    },
    {
        constants.MFA_METHOD_LABEL: constants.MFA_VIA_SMS,
        SELECT_CSS_SELECTORS_LABEL: '#ius-mfa-sms-otp-card-challenge, [data-testid="challengePickerOption_SMS_OTP"]',
        INPUT_CSS_SELECTORS_LABEL: "#ius-mfa-confirm-code",
        SPAN_CSS_SELECTORS_LABEL: '[data-testid="VerifyOtpHeaderText"], #VerifyOtpHeader',
        BUTTON_CSS_SELECTORS_LABEL: '#ius-mfa-otp-submit-btn, [data-testid="VerifyOtpSubmitButton"]',
    },
]

DEFAULT_MFA_INPUT_PROMPT = "Please enter your 6-digit MFA code: "

STANDARD_MISSING_EXCEPTIONS = (
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotVisibleException,
)


def get_email_code(imap_account, imap_password, imap_server, imap_folder, delete=True):
    code = None
    try:
        imap_client = imaplib.IMAP4_SSL(imap_server)
    except imaplib.IMAP4.error:
        raise RuntimeError("Unable to establish IMAP Client")

    try:
        rv, data = imap_client.login(imap_account, imap_password)
    except imaplib.IMAP4.error:
        raise RuntimeError("Unable to login to IMAP Email")

    code = ""
    for c in range(20):
        time.sleep(10)
        rv, data = imap_client.select(imap_folder)
        if rv != "OK":
            raise RuntimeError("Unable to open mailbox: " + rv)

        rv, data = imap_client.search(None, "ALL")
        if rv != "OK":
            raise RuntimeError("Unable to search the Email folder: " + rv)

        count = 0
        for num in data[0].split()[::-1]:
            count = count + 1
            if count > 3:
                break
            rv, data = imap_client.fetch(num, "(BODY.PEEK[])")
            if rv != "OK":
                raise RuntimeError("Unable to complete due to error message: " + rv)

            msg = email.message_from_bytes(data[0][1])

            x = email.header.make_header(email.header.decode_header(msg["Subject"]))
            subject = str(x)
            logger.debug("DEBUG: SUBJECT:", subject)

            x = email.header.make_header(email.header.decode_header(msg["From"]))
            frm = str(x)
            logger.debug("DEBUG: FROM:", frm)

            if not re.search("do_not_reply@intuit.com", frm, re.IGNORECASE):
                continue

            p = re.search(r"(\d\d\d\d\d\d) Mint code", subject)
            if p:
                code = p.group(1)
            elif not re.search("Your Mint (code|Account)", subject, re.IGNORECASE):
                continue
            else:
                code = ""

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

            if code == "":
                body = next(msg.walk()).get_payload(None, True).decode()
                p = re.search(
                    r"Verification code:<.*?(\d\d\d\d\d\d)\b", body, re.S | re.M
                )
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
    fail_if_stale=False,
    imap_account=None,
    imap_password=None,
    imap_server=None,
    imap_folder="INBOX",
    beta=False,
):
    if beta:
        url = constants.MINT_BETA_ROOT_URL
    else:
        url = constants.MINT_ROOT_URL
    """
    Takes in a web driver and gets it through the Mint sign in process
    """
    driver.implicitly_wait(20)  # seconds
    driver.get(url)
    if not beta:
        # Add 1 second delay otherwise an issue occurs when trying to click the sign in button on home page
        time.sleep(1)
        home_page(driver)

    WebDriverWait(driver, 20).until(
        expected_conditions.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                ".ius-hosted-ui-main-container, #ius-link-use-a-different-id-known-device, #ius-userid, "
                '#ius-identifier, #ius-option-username, [data-testid="IdentifierFirstSubmitButton"]',
            )
        )
    )

    driver.implicitly_wait(0)  # seconds

    user_selection_page(driver)

    driver.implicitly_wait(1)  # seconds
    count = 0
    while not driver.current_url.startswith("{}/".format(url)):
        try:  # try to enter in credentials if username and password are on same page
            handle_same_page_username_password(driver, email, password)
        except (
            ElementNotInteractableException,
            ElementNotVisibleException,
            NoSuchElementException,
        ):
            try:  # try to enter in credentials if username and password are on different pages
                handle_different_page_username_password(driver, email)
                driver.implicitly_wait(5)  # seconds
                password_page(driver, password)
            except (
                ElementNotInteractableException,
                ElementNotVisibleException,
                NoSuchElementException,
            ):
                # no need to enter credentials, likely alreadly logged in
                pass
            driver.implicitly_wait(1)  # seconds

        # Wait until logged in, just in case we need to deal with MFA.

        handle_login_failures(driver)
        if not bypass_verified_user_page(driver):
            # if bypass_verified_user_page was present, then MFA already done
            bypass_passwordless_login_page(driver)
            if mfa_method is not None:
                mfa_selection_page(driver, mfa_method)
            mfa_page(
                driver,
                mfa_method,
                mfa_token,
                mfa_input_callback,
                imap_account,
                imap_password,
                imap_server,
                imap_folder,
            )
        account_selection_page(driver, intuit_account)
        password_page(driver, password)
        # Give the overview page a chance to actually load.
        # If it doesn't, then there may be another round of MFA.
        try:
            WebDriverWait(driver, 5).until(
                expected_conditions.url_contains("{}/".format(url))
            )
        except Exception:
            count += 1
            if count > 4:
                raise RuntimeError(
                    "Login to Mint failed due to timeout in the Multifactor Method Loop"
                )

    driver.implicitly_wait(20)  # seconds
    # Wait until the overview page has actually loaded, and if wait_for_sync==True, sync has completed.
    status_message = None
    if wait_for_sync:
        status_message = handle_wait_for_sync(
            driver, wait_for_sync_timeout, fail_if_stale
        )
    return status_message


def home_page(driver):
    try:
        element = driver.find_element(By.LINK_TEXT, "Sign in").click()
    except WebDriverException:
        logger.info("WebDriverException when clicking Sign In")


def user_selection_page(driver):
    # click "Use a different user ID" if needed
    try:
        driver.find_element(By.ID, "ius-link-use-a-different-id-known-device").click()
        WebDriverWait(driver, 20).until(
            expected_conditions.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    '#ius-userid, #ius-identifier, #ius-option-username, [data-testid="IdentifierFirstSubmitButton"]',
                )
            )
        )
    except NoSuchElementException:
        pass


def handle_same_page_username_password(driver, email, password):
    email_input = driver.find_element(By.ID, "ius-userid")
    if not email_input.is_displayed():
        raise ElementNotVisibleException()
    email_input.clear()  # clear email and user specified email
    email_input.send_keys(email)
    driver.find_element(By.ID, "ius-password").send_keys(password)
    driver.find_element(
        By.CSS_SELECTOR,
        '#ius-sign-in-submit-btn, [data-testid="IdentifierFirstSubmitButton"]',
    ).submit()


def handle_different_page_username_password(driver, email):
    try:
        email_input = driver.find_element(
            By.CSS_SELECTOR,
            '#ius-identifier, [data-testid="IdentifierFirstIdentifierInput"]',
        )
        if not email_input.is_displayed():
            raise ElementNotVisibleException()
        email_input.clear()  # clear email and use specified email
        email_input.send_keys(email)
        driver.find_element(
            By.CSS_SELECTOR,
            '#ius-identifier-first-submit-btn, [data-testid="IdentifierFirstSubmitButton"]',
        ).click()

    # click on username if on the saved usernames page
    except (ElementNotInteractableException, ElementNotVisibleException):
        username_elements = driver.find_element(By.CLASS_NAME, "ius-option-username")
        for username_element in username_elements:
            if username_element.text == email:
                username_element.click()
                break


def handle_login_failures(driver):
    try:
        WebDriverWait(driver, 0).until(
            expected_conditions.presence_of_element_located(
                (
                    By.XPATH,
                    '//div[contains(text(), "We can\'t find anyone with ")][@id="ius-identifier-first-error"]',
                )
            )
        )
        raise RuntimeError(
            "Login to Mint failed: Mint does not recognize your login email"
        )
    except TimeoutException:
        pass

    try:
        WebDriverWait(driver, 0).until(
            expected_conditions.presence_of_element_located(
                (
                    By.XPATH,
                    "//div[contains(text(), 'The password you entered is incorrect.')]",
                )
            )
        )
        raise RuntimeError("Login to Mint failed: incorrect password")
    except TimeoutException:
        pass

    try:
        WebDriverWait(driver, 0).until(
            expected_conditions.presence_of_element_located(
                (
                    By.ID,
                    "RecaptchaHeader",
                )
            )
        )
        raise RuntimeError("Login to Mint failed: Captcha presented")
    except TimeoutException:
        pass

    try:
        WebDriverWait(driver, 0).until(
            expected_conditions.presence_of_element_located(
                (
                    By.XPATH,
                    '//h2[contains(text(), "The feature you\'ve requested is temporarily unavailable")]',
                )
            )
        )
        raise RuntimeError(
            "Login to Mint failed: Mint reports that it's temporarily unavailable: you may be blocked."
        )
    except TimeoutException:
        pass


def bypass_verified_user_page(driver):
    # bypass "Let's add your current mobile number" interstitial page
    # returns True is page is bypassed
    try:
        skip_for_now = driver.find_element(
            By.CSS_SELECTOR,
            '#ius-verified-user-update-btn-skip, [data-testid="VUUSkipButton"]',
        ).click()
        return True
    except (
        NoSuchElementException,
        StaleElementReferenceException,
        ElementNotVisibleException,
        ElementNotInteractableException,
    ):
        return False


def mfa_selection_page(driver, mfa_method):
    try:
        driver.find_element(By.ID, "ius-mfa-options-form")
        mfa_method_option = driver.find_element(
            By.ID, "ius-mfa-option-{}".format(mfa_method)
        )
        mfa_method_option.click()
        mfa_method_submit = driver.find_element(By.ID, "ius-mfa-options-submit-btn")
        mfa_method_submit.click()
    except STANDARD_MISSING_EXCEPTIONS:
        pass


def bypass_passwordless_login_page(driver):
    # bypass "Sign in without a password next time" interstitial page
    try:
        skip_for_now = driver.find_element(
            By.CSS_SELECTOR, "#skipWebauthnRegistration, #signInDifferentWay"
        ).click()
    except (
        NoSuchElementException,
        StaleElementReferenceException,
        ElementNotVisibleException,
        ElementNotInteractableException,
    ):
        pass
    # bypass "Let's make sure you're you" if password login is allowed
    try:
        skip_for_now = driver.find_element(
            By.CSS_SELECTOR,
            '[data-testid="challengePickerOption_PASSWORD"]',
        ).click()
    except (
        NoSuchElementException,
        StaleElementReferenceException,
        ElementNotVisibleException,
        ElementNotInteractableException,
    ):
        pass


def mfa_page(
    driver,
    mfa_method,
    mfa_token,
    mfa_input_callback,
    imap_account,
    imap_password,
    imap_server,
    imap_folder,
):
    if mfa_method is None:
        mfa_result = search_mfa_method(driver)
    else:
        try:
            mfa_result = set_mfa_method(driver, mfa_method)
        except MFAMethodNotAvailableError as e:
            # MFA is optional for devices that were registered to Mint by clicking on "Remember my device"
            logger.info(str(e))
            return
    mfa_token_input = mfa_result[0]
    mfa_token_button = mfa_result[1]
    mfa_method = mfa_result[2]
    if mfa_method is None:
        # MFA is optional for devices that were registered to Mint by clicking on "Remember my device"
        logger.info("Your Mint Account does not require Multifactor Authentication.")
        return

    # mfa screen
    if mfa_method == constants.MFA_VIA_SOFT_TOKEN:
        handle_soft_token(
            mfa_token_input, mfa_token_button, mfa_input_callback, mfa_token
        )
    elif mfa_method == constants.MFA_VIA_EMAIL and imap_account:
        handle_email_by_imap(
            mfa_token_input,
            mfa_token_button,
            mfa_input_callback,
            imap_account,
            imap_password,
            imap_server,
            imap_folder,
        )
    else:
        handle_other_mfa(mfa_token_input, mfa_token_button, mfa_input_callback)


def search_mfa_method(driver):
    for method in MFA_METHODS:
        mfa_token_input = mfa_token_button = mfa_method = span_text = result = None
        try:
            mfa_token_input = driver.find_element(
                By.CSS_SELECTOR, method[INPUT_CSS_SELECTORS_LABEL]
            )
            mfa_token_button = driver.find_element(
                By.CSS_SELECTOR, method[BUTTON_CSS_SELECTORS_LABEL]
            )
            mfa_method = method[constants.MFA_METHOD_LABEL]
            span_text = driver.find_element(
                By.CSS_SELECTOR, method[SPAN_CSS_SELECTORS_LABEL]
            ).text.lower()
            if span_text is not None:
                result = mfa_method in span_text
                if result is True:
                    break
        except (NoSuchElementException, ElementNotInteractableException):
            logger.info("{} MFA Method Not Found".format(constants.MFA_METHOD_LABEL))
    return mfa_token_input, mfa_token_button, mfa_method


def set_mfa_method(driver, mfa_method):
    mfa = filter(
        lambda method: method[constants.MFA_METHOD_LABEL] == mfa_method,
        MFA_METHODS,
    )
    mfa_result = list(mfa)[0]
    try:
        mfa_token_select = driver.find_element(
            By.CSS_SELECTOR, mfa_result[SELECT_CSS_SELECTORS_LABEL]
        ).click()
        mfa_token_input = driver.find_element(
            By.CSS_SELECTOR, mfa_result[INPUT_CSS_SELECTORS_LABEL]
        )
        mfa_token_button = driver.find_element(
            By.CSS_SELECTOR, mfa_result[BUTTON_CSS_SELECTORS_LABEL]
        )
        mfa_method = mfa_result[constants.MFA_METHOD_LABEL]
    except (NoSuchElementException, ElementNotInteractableException) as e:
        raise MFAMethodNotAvailableError(
            "The Multifactor Method {} supplied is not available.".format(mfa_method)
        ) from e
    return mfa_token_input, mfa_token_button, mfa_method


def handle_soft_token(mfa_token_input, mfa_token_button, mfa_input_callback, mfa_token):
    try:
        if mfa_token is not None:
            mfa_code = oathtool.generate_otp(mfa_token)
        else:
            mfa_code = (mfa_input_callback or input)(DEFAULT_MFA_INPUT_PROMPT)
        submit_mfa_code(mfa_token_input, mfa_token_button, mfa_code)
    except (NoSuchElementException, ElementNotInteractableException):
        logger.info("Not on Soft Token MFA Screen")


def handle_email_by_imap(
    mfa_token_input,
    mfa_token_button,
    mfa_input_callback,
    imap_account,
    imap_password,
    imap_server,
    imap_folder,
):
    try:
        mfa_code = get_email_code(
            imap_account,
            imap_password,
            imap_server,
            imap_folder,
        )
        if mfa_code is None:
            mfa_code = (mfa_input_callback or input)(DEFAULT_MFA_INPUT_PROMPT)
        submit_mfa_code(mfa_token_input, mfa_token_button, mfa_code)
    except (NoSuchElementException, ElementNotInteractableException, EOFError):
        logger.info("Not on Email MFA Screen")


def handle_other_mfa(mfa_token_input, mfa_token_button, mfa_input_callback):
    try:
        mfa_code = (mfa_input_callback or input)(DEFAULT_MFA_INPUT_PROMPT)
        submit_mfa_code(mfa_token_input, mfa_token_button, mfa_code)
    except (NoSuchElementException, ElementNotInteractableException, EOFError):
        logger.info("Not on SMS or Authenticator MFA Screen")


def submit_mfa_code(mfa_token_input, mfa_token_button, mfa_code):
    mfa_token_input.clear()
    mfa_token_input.send_keys(mfa_code)
    mfa_token_button.click()


def account_selection_page(driver, intuit_account):
    # account selection screen -- if there are multiple accounts, select one
    try:
        WebDriverWait(driver, 20).until(
            expected_conditions.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    '[data-testid="SelectAccountForm"], [data-testid="IdFirstKnownContainer"]',
                )
            )
        )
        select_account = driver.find_element(
            By.CSS_SELECTOR,
            '[data-testid="SelectAccountForm"], [data-testid="IdFirstKnownContainer"]',
        )
        if intuit_account is not None:
            account_input = select_account.find_element(
                By.XPATH,
                "//*/span[text()='{}']/../../../preceding-sibling::input".format(
                    intuit_account
                ),
            )
            # NOTE: We need to execute a script because simply using account_input.click()
            #       results in ElementClickInterceptedException.
            driver.execute_script("arguments[0].click()", account_input)

        WebDriverWait(driver, 20).until(
            expected_conditions.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "#ius-sign-in-mfa-select-account-continue-btn, [data-testid='SelectAccountContinueButton'], [data-testid='AccountChoiceUsage_0']",
                )
            )
        )
        driver.find_element(
            By.CSS_SELECTOR,
            '#ius-sign-in-mfa-select-account-continue-btn, [data-testid="SelectAccountContinueButton"], [data-testid="AccountChoiceUsage_0"]',
        ).click()
    except (TimeoutException, NoSuchElementException):
        logger.info("Not on Account Selection Screen")


def password_page(driver, password):
    # password only sometimes after mfa
    try:
        driver.find_element(
            By.CSS_SELECTOR,
            "#iux-password-confirmation-password, #ius-sign-in-mfa-password-collection-current-password",
        ).send_keys(password)
        driver.find_element(
            By.CSS_SELECTOR,
            '#ius-sign-in-mfa-password-collection-continue-btn, [data-testid="passwordVerificationContinueButton"]',
        ).submit()
    except (
        NoSuchElementException,
        StaleElementReferenceException,
        ElementNotVisibleException,
        ElementNotInteractableException,
    ):
        logger.info("Not on Secondary MFA Password Screen")


def handle_wait_for_sync(driver, wait_for_sync_timeout, fail_if_stale):
    try:
        # Status message might not be present straight away. Seems to be due
        # to dynamic content (client side rendering).
        status_web_element = WebDriverWait(driver, 30).until(
            expected_conditions.visibility_of_element_located(
                (By.CSS_SELECTOR, ".AccountStatusBar")
            )
        )

        def refresh_complete(x):
            statusHtml = status_web_element.get_attribute("innerHTML")

            return ("Account refresh complete" in statusHtml) or (
                "We can't update your" in statusHtml
            )

        WebDriverWait(driver, wait_for_sync_timeout).until(refresh_complete)
        return status_web_element.text
    except (TimeoutException, StaleElementReferenceException):
        logger.warning(exceptions.STALE_DATA_ERROR_MESSAGE)
        if fail_if_stale:
            raise exceptions.StaleDataException
    except (exceptions.StaleDataException):
        sys.exit(1)

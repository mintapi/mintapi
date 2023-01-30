"""
Selenium Browser
"""
import logging
import os

from mintapi.constants import JSON_HEADER, MINT_CREDIT_URL
from mintapi.endpoints import MintEndpoints
from mintapi.signIn import _create_web_driver_at_mint_com, sign_in

logger = logging.getLogger("mintapi")


def reverse_credit_amount(row):
    amount = float(row["amount"][1:].replace(",", ""))
    return amount if row["isDebit"] else -amount


class SeleniumBrowser(MintEndpoints):
    """
    Selenium based browser to manage auth interaction
    """

    # TODO: did not give much attention to this class. mostly a direct move from the original Mint class

    driver = None
    status_message = None

    def __init__(
        self,
        email=None,
        password=None,
        mfa_method=None,
        mfa_token=None,
        mfa_input_callback=None,
        intuit_account=None,
        headless=False,
        session_path=None,
        imap_account=None,
        imap_password=None,
        imap_server=None,
        imap_folder="INBOX",
        wait_for_sync=True,
        wait_for_sync_timeout=5 * 60,
        fail_if_stale=False,
        use_chromedriver_on_path=False,
        chromedriver_download_path=os.getcwd(),
        driver=None,
        beta=False,
        quit_driver_on_fail=True,
    ):
        self.driver = None
        self.status_message = None
        self.quit_driver_on_fail = quit_driver_on_fail

        if email and password:
            self.login_and_get_token(
                email,
                password,
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
                fail_if_stale=fail_if_stale,
                use_chromedriver_on_path=use_chromedriver_on_path,
                chromedriver_download_path=chromedriver_download_path,
                driver=driver,
                beta=beta,
            )

    """
    Selenium Interaction
    """

    def close(self):
        """Logs out and quits the current web driver/selenium session."""
        if not self.driver:
            return

        self.driver.quit()
        self.driver = None

    def login_and_get_token(
        self,
        email,
        password,
        mfa_method=None,
        mfa_token=None,
        mfa_input_callback=None,
        intuit_account=None,
        headless=False,
        session_path=None,
        imap_account=None,
        imap_password=None,
        imap_server=None,
        imap_folder=None,
        wait_for_sync=True,
        wait_for_sync_timeout=5 * 60,
        fail_if_stale=False,
        use_chromedriver_on_path=False,
        chromedriver_download_path=os.getcwd(),
        driver=None,
        beta=False,
    ):

        self.driver = driver or _create_web_driver_at_mint_com(
            headless, session_path, use_chromedriver_on_path, chromedriver_download_path
        )

        try:
            self.status_message = sign_in(
                email,
                password,
                self.driver,
                mfa_method,
                mfa_token,
                mfa_input_callback,
                intuit_account,
                wait_for_sync,
                wait_for_sync_timeout,
                fail_if_stale,
                imap_account,
                imap_password,
                imap_server,
                imap_folder,
                beta,
            )
        except Exception as e:
            msg = f"Could not sign in to Mint. Current page: {self.driver.current_url}"
            logger.exception(e)
            if self.quit_driver_on_fail:
                self.driver.quit()
                self.driver = None
            raise Exception(msg) from e

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

    def _load_mint_credit_url(self):
        # Because cookies are involved and you cannot add cookies for another
        # domain, we have to first load up the MINT_CREDIT_URL.  Once the new
        # domain has loaded, we can proceed with the pull of credit data.
        return self.driver.get(MINT_CREDIT_URL)

    """
    Accessor Methods
    """

    def request(
        self,
        *,
        method: str,
        api_url: str,
        api_section: str,
        uri_path: str,
        data_key: str,
        metadata_key: str,
        paginate=True,
        headers=None,
        **kwargs,
    ):
        url = f"{api_url}{api_section}{uri_path}"

        # inject headers for each request
        if headers is None:
            headers = {}
        auth_headers = self._get_api_key_header()
        auth_headers.update(headers)

        response = self.driver.request(
            method=method, url=url, headers=auth_headers, **kwargs
        )
        response.raise_for_status()

        if paginate:
            return self._paginate(
                api_url=api_url,
                api_section=api_section,
                method=method,
                data_key=data_key,
                metadata_key=metadata_key,
                response=response,
                headers=headers,
                **kwargs,
            )
        else:
            return response

    """
    Session Extraction
    """

    def _get_api_key_header(self):
        key_var = "window.__shellInternal.appExperience.appApiKey"
        api_key = self.driver.execute_script("return " + key_var)
        auth = "Intuit_APIKey intuit_apikey=" + api_key
        auth += ", intuit_apikey_version=1.0"
        header = {"authorization": auth}
        header.update(JSON_HEADER)
        return header

    def _get_cookies(self):
        return self.driver.get_cookies()

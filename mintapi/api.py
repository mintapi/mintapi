import logging
import os
from datetime import date, datetime
from typing import Dict, List, Optional
from dateutil.relativedelta import relativedelta

from mintapi import constants
from mintapi.signIn import _create_web_driver_at_mint_com, sign_in
from mintapi.transactions import TransactionRequest
from mintapi.trends import ReportView, TrendRequest

from mintapi.filters import (
    AccountIdFilter,
    CategoryIdFilter,
    DateFilter,
    DescriptionNameFilter,
    SearchFilter,
    TagIdFilter,
)

logger = logging.getLogger("mintapi")

ENDPOINTS = {
    constants.ACCOUNT_KEY: {
        "apiVersion": "pfm/v1",
        "endpoint": "accounts",
        "beginningDate": None,
        "endingDate": None,
        "includeCreatedDate": True,
        "includeUpdatedDate": True,
    },
    constants.BUDGET_KEY: {
        "apiVersion": "pfm/v1",
        "endpoint": "budgets",
        "beginningDate": "startDate",
        "endingDate": "endDate",
        "includeCreatedDate": True,
        "includeUpdatedDate": True,
    },
    constants.CATEGORY_KEY: {
        "apiVersion": "pfm/v1",
        "endpoint": "categories",
        "beginningDate": None,
        "endingDate": None,
        "includeCreatedDate": False,
        "includeUpdatedDate": True,
    },
    constants.INVESTMENT_KEY: {
        "apiVersion": "pfm/v1",
        "endpoint": "investments",
        "beginningDate": None,
        "endingDate": None,
        "includeCreatedDate": False,
        "includeUpdatedDate": True,
    },
    constants.TRANSACTION_KEY: {
        "apiVersion": "pfm/v1",
        "endpoint": "transactions/search",
        "beginningDate": "fromDate",
        "endingDate": "toDate",
        "includeCreatedDate": False,
        "includeUpdatedDate": True,
    },
    constants.TRENDS_KEY: {
        "apiVersion": "pfm/v1",
        "endpoint": "trends",
        "beginningDate": "fromDate",
        "endingDate": "toDate",
        "includeCreatedDate": False,
        "includeUpdatedDate": False,
    },
}


def convert_mmddyy_to_yyyymmdd(date):
    try:
        newdate = datetime.strptime(date, "%m/%d/%y").strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        newdate = None
    return newdate


def reverse_credit_amount(row):
    amount = float(row["amount"][1:].replace(",", ""))
    return amount if row["isDebit"] else -amount


class MintException(Exception):
    pass


class Mint(object):
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
    ):
        self.driver = None
        self.status_message = None

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

    def _get_api_key_header(self):
        key_var = "window.__shellInternal.appExperience.appApiKey"
        api_key = self.driver.execute_script("return " + key_var)
        auth = "Intuit_APIKey intuit_apikey=" + api_key
        auth += ", intuit_apikey_version=1.0"
        header = {"authorization": auth}
        header.update(constants.JSON_HEADER)
        return header

    def close(self):
        """Logs out and quits the current web driver/selenium session."""
        if not self.driver:
            return

        self.driver.quit()
        self.driver = None

    def get(self, url, **kwargs):
        return self.driver.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.driver.request("POST", url, **kwargs)

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

    def get_bills(self):
        return self.get(
            "{}/bps/v2/payer/bills".format(constants.MINT_ROOT_URL),
            headers=self._get_api_key_header(),
        ).json()["bills"]

    def get_data(self, method, name, payload=None, **kwargs):
        endpoint = self.__find_endpoint(name)
        if method == "POST":
            data = self.__post_mint_endpoint(endpoint, payload)
        else:
            data = self.__get_mint_endpoint(endpoint, **kwargs)
        if name in data.keys():
            for i in data[name]:
                if endpoint["includeCreatedDate"]:
                    i["createdDate"] = i["metaData"]["createdDate"]
                if endpoint["includeUpdatedDate"]:
                    i["lastUpdatedDate"] = i["metaData"]["lastUpdatedDate"]
                i.pop("metaData", None)
        else:
            raise MintException(
                "Data from the {} endpoint did not containt the expected {} key.".format(
                    endpoint["endpoint"], name
                )
            )
        return data[name]

    def get_account_data(
        self,
        limit=5000,
    ):
        return self.get_data(
            method=constants.GET_METHOD, name=constants.ACCOUNT_KEY, limit=limit
        )

    def get_category_data(
        self,
        limit=5000,
    ):
        return self.get_data(
            method=constants.GET_METHOD, name=constants.CATEGORY_KEY, limit=limit
        )

    def get_budget_data(
        self,
        limit=5000,
    ):
        return self.get_data(
            method=constants.GET_METHOD,
            name=constants.BUDGET_KEY,
            payload=None,
            limit=limit,
            id=None,
            start_date=self.__x_months_ago(11),
            end_date=self.__first_of_this_month(),
        )

    def get_investment_data(
        self,
        limit=5000,
    ):
        return self.get_data(
            method=constants.GET_METHOD,
            name=constants.INVESTMENT_KEY,
            limit=limit,
        )

    def get_net_worth_data(self, account_data=None):
        if account_data is None:
            account_data = self.get_account_data()

        # account types in this list will be subtracted
        invert = set(["LoanAccount", "CreditAccount"])
        return sum(
            [
                -a["currentBalance"] if a["type"] in invert else a["currentBalance"]
                for a in account_data
                if a["isActive"] and "currentBalance" in a
            ]
        )

    def initiate_account_refresh(self):
        self.post(
            url="{}/refreshFILogins.xevent".format(constants.MINT_ROOT_URL),
            headers=constants.JSON_HEADER,
        )

    def get_credit_score_data(self):
        # Request a single credit report, and extract the score
        report = self.get_credit_report_data(
            limit=1,
            details=False,
            exclude_inquiries=False,
            exclude_accounts=False,
            exclude_utilization=False,
        )
        try:
            vendor = report["reports"]["vendorReports"][0]
            return vendor["creditReportList"][0]["creditScore"]
        except (KeyError, IndexError):
            raise Exception("No Credit Score Found")

    def get_credit_report_data(
        self,
        limit=2,
        details=True,
        exclude_inquiries=False,
        exclude_accounts=False,
        exclude_utilization=False,
    ):
        # Get the browser API key, build auth header
        credit_header = self._get_api_key_header()

        # Get credit reports. The UI shows 2 by default, but more are available!
        # At least 8, but could be all the TransUnion reports Mint has
        # How the "bands" are defined, and other metadata, is available at a
        # /v1/creditscoreproviders/3 endpoint (3 = TransUnion)
        credit_report = dict()

        self._load_mint_credit_url()

        credit_report["reports"] = self._get_credit_reports(limit, credit_header)

        # If we want details, request the detailed sub-reports
        if details:
            # Get full list of credit inquiries
            if not exclude_inquiries:
                credit_report["inquiries"] = self.get_credit_inquiries(credit_header)

            # Get full list of credit accounts
            if not exclude_accounts:
                credit_report["accounts"] = self.get_credit_accounts(credit_header)

            # Get credit utilization history (~3 months, by account)
            if not exclude_utilization:
                credit_report["utilization"] = self.get_credit_utilization(
                    credit_header
                )

        return credit_report

    def _load_mint_credit_url(self):
        # Because cookies are involved and you cannot add cookies for another
        # domain, we have to first load up the MINT_CREDIT_URL.  Once the new
        # domain has loaded, we can proceed with the pull of credit data.
        return self.driver.get(constants.MINT_CREDIT_URL)

    def _get_credit_reports(self, limit, credit_header):
        return self.get(
            "{}/v1/creditreports?limit={}".format(constants.MINT_CREDIT_URL, limit),
            headers=credit_header,
        ).json()

    def _get_credit_details(self, url, credit_header):
        return self.get(
            url.format(constants.MINT_CREDIT_URL), headers=credit_header
        ).json()

    def get_credit_inquiries(self, credit_header):
        return self._get_credit_details(
            "{}/v1/creditreports/0/inquiries", credit_header
        )

    def get_credit_accounts(self, credit_header):
        return self._get_credit_details(
            "{}/v1/creditreports/0/tradelines", credit_header
        )

    def get_credit_utilization(self, credit_header):
        return self._process_utilization(
            self._get_credit_details(
                "{}/v1/creditreports/creditutilizationhistory", credit_header
            )
        )

    def _process_utilization(self, data):
        # Function to clean up the credit utilization history data
        utilization = []
        utilization.extend(self._flatten_utilization(data["cumulative"]))
        for trade in data["tradelines"]:
            utilization.extend(self._flatten_utilization(trade))
        return utilization

    def _flatten_utilization(self, data):
        # The utilization history data has a nested format, grouped by year
        # and then by month. Let's flatten that into a list of dates.
        utilization = []
        name = data.get("creditorName", "Total")
        for cu in data["creditUtilization"]:
            year = cu["year"]
            for cu_month in cu["months"]:
                date = datetime.strptime(cu_month["name"], "%B").replace(
                    day=1, year=int(year)
                )
                utilization.append(
                    {
                        "name": name,
                        "date": date.strftime("%Y-%m-%d"),
                        "utilization": cu_month["creditUtilization"],
                    }
                )
        return utilization

    def __find_endpoint(self, name):
        return ENDPOINTS[name]

    def __get_mint_endpoint(
        self, endpoint, limit=5000, id=None, start_date=None, end_date=None
    ):
        url = "{}/{}/{}?limit={}&".format(
            constants.MINT_ROOT_URL, endpoint["apiVersion"], endpoint["endpoint"], limit
        )
        if endpoint["beginningDate"] is not None and start_date is not None:
            url = url + "{}={}&".format(endpoint["beginningDate"], start_date)
        if endpoint["endingDate"] is not None and end_date is not None:
            url = url + "{}={}&".format(endpoint["endingDate"], end_date)
        if id is not None:
            url = url + "id={}&".format(id)
        response = self.get(
            url,
            headers=self._get_api_key_header(),
        )
        return response.json()

    def __post_mint_endpoint(self, endpoint, payload):
        url = "{}/{}/{}".format(
            constants.MINT_ROOT_URL, endpoint["apiVersion"], endpoint["endpoint"]
        )
        response = self.post(
            url, json=payload.to_dict(), headers=self._get_api_key_header()
        )
        return response.json()

    def __first_of_this_month(self):
        return date.today().replace(day=1)

    def __x_months_ago(self, months=2):
        return (self.__first_of_this_month() - relativedelta(months=months)).replace(
            day=1
        )

    def get_trend_data(
        self,
        report_type: ReportView.Options = ReportView.Options.SPENDING_TIME,
        date_filter: DateFilter.Options = DateFilter.Options.THIS_MONTH,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category_ids: List[str] = None,
        tag_ids: List[str] = None,
        descriptions: List[str] = None,
        account_ids: List[str] = None,
        match_all_filters: bool = True,
        limit: int = 5000,
        offset: int = 0,
    ) -> List[Dict]:
        """
        Public accessor for trend data. Internally constructs a trend api payload


        Parameters
        ----------
        report_type : ReportView.Options
            type of report to generate. must use one of enum values
        date_filter : DateFilter.Options
            date window. must use predefined enum windows or pass a start and end date with CUSTOM enum
        start_date : Optional[str], optional
            optional start date (mm-dd-yy) if using enum CUSTOM, by default None
        end_date : Optional[str], optional
            optional end date (mm-dd-yy) if using enum CUSTOM, by default None
        category_ids : List[str], optional
            optional list of category ids to filter by, by default None
        tag_ids : List[str], optional
            optional list of tag ids to filter by, by default None
        descriptions : List[str], optional
            optional list of descriptions (ui labeled merchants) to filter by, by default None
        account_ids : List[str], optional
            optional list of account ids to filter by, default None
        match_all_filters : bool, optional
            whether to match all (True) supplied filters or any (False), by default True
        limit : int, optional
            page size, by default 5000
        offset : int, optional
            offset pagination for next pages, by default 0

        Returns
        -------
        List[Dict]
            returns a list of trend results (each dict)
        """
        search_clauses = self.__build_search_clauses(
            category_ids, tag_ids, descriptions, account_ids
        )
        payload = self.__build_payload(
            request=TrendRequest,
            report_type=report_type,
            date_filter=date_filter,
            start_date=start_date,
            end_date=end_date,
            match_all_filters=match_all_filters,
            limit=limit,
            offset=offset,
            search_clauses=search_clauses,
        )
        data = self.get_data(constants.POST_METHOD, constants.TRENDS_KEY, payload)
        return data

    def get_transaction_data(
        self,
        date_filter: DateFilter.Options = DateFilter.Options.ALL_TIME,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category_ids: List[str] = None,
        tag_ids: List[str] = None,
        descriptions: List[str] = None,
        account_ids: List[str] = None,
        match_all_filters: bool = True,
        include_investment: bool = False,
        remove_pending: bool = True,
        limit: int = 5000,
        offset: int = 0,
    ) -> List[Dict]:
        """
        Public accessor for transaction data. Internally constructs a transaction/search api payload


        Parameters
        ----------
        date_filter : DateFilter.Options
            date window. must use predefined enum windows or pass a start and end date with CUSTOM enum
        start_date : Optional[str], optional
            optional start date (mm-dd-yy) if using enum CUSTOM, by default None
        end_date : Optional[str], optional
            optional end date (mm-dd-yy) if using enum CUSTOM, by default None
        category_ids : List[str], optional
            optional list of category ids to filter by, by default None
        tag_ids : List[str], optional
            optional list of tag ids to filter by, by default None
        descriptions : List[str], optional
            optional list of descriptions (ui labeled merchants) to filter by, by default None
        account_ids : List[str], optional
            optional list of account ids to filter by, default None
        match_all_filters : bool, optional
            whether to match all (True) supplied filters or any (False), by default True
        include_investment : bool, optional
            whether to include transactions of type InvestmentTransaction; by default, this is False
        remove_pending : bool, optional
            whether to include transactions that are still Pending; by default, this is True
        limit : int, optional
            page size, by default 5000
        offset : int, optional
            offset pagination for next pages, by default 0

        Returns
        -------
        List[Dict]
            returns a list of transaction results (each dict)
        """
        search_clauses = self.__build_search_clauses(
            category_ids, tag_ids, descriptions, account_ids
        )

        payload = self.__build_payload(
            request=TransactionRequest,
            report_type=None,
            date_filter=date_filter,
            start_date=start_date,
            end_date=end_date,
            match_all_filters=match_all_filters,
            limit=limit,
            offset=offset,
            search_clauses=search_clauses,
        )
        data = self.get_data(constants.POST_METHOD, constants.TRANSACTION_KEY, payload)
        if remove_pending:
            filtered = filter(
                lambda transaction: transaction["isPending"] == False,
                data,
            )
            data = list(filtered)
        if not include_investment:
            filtered = filter(
                lambda transaction: transaction["type"] != "InvestmentTransaction",
                data,
            )
            data = list(filtered)
        return data

    def __build_search_clauses(self, category_ids, tag_ids, descriptions, account_ids):
        search_clauses = []
        include_child_categories = True
        if category_ids:
            search_clauses = self.__append_filter(
                CategoryIdFilter, search_clauses, tag_ids, include_child_categories
            )
        if tag_ids:
            search_clauses = self.__append_filter(TagIdFilter, search_clauses, tag_ids)
        if descriptions:
            search_clauses = self.__append_filter(
                DescriptionNameFilter, search_clauses, descriptions
            )
        if account_ids:
            search_clauses = self.__append_filter(
                AccountIdFilter, search_clauses, account_ids
            )
        return search_clauses

    def __build_payload(
        self,
        request,
        report_type,
        date_filter,
        start_date,
        end_date,
        match_all_filters,
        limit,
        offset,
        search_clauses,
    ):
        return request(
            date_filter=DateFilter(
                date_filter=date_filter,
                start_date=convert_mmddyy_to_yyyymmdd(start_date),
                end_date=convert_mmddyy_to_yyyymmdd(end_date),
            ),
            search_filters=SearchFilter(
                match_all_filters=search_clauses if match_all_filters else [],
                match_any_filters=search_clauses if not match_all_filters else [],
            ),
            report_view=ReportView(report_type=report_type)
            if report_type is not None
            else None,
            limit=limit,
            offset=offset,
        )

    def __append_filter(self, filter, search_clauses, values, **kwargs):
        for value in values:
            search_clauses.append(filter(value=value, **kwargs))
        return search_clauses


def get_accounts(email, password, get_detail=False):
    mint = Mint(email, password)
    return mint.get_account_data(get_detail=get_detail)


def get_net_worth(email, password):
    mint = Mint(email, password)
    account_data = mint.get_account_data()
    return mint.get_net_worth(account_data)


def get_budgets(email, password):
    mint = Mint(email, password)
    return mint.get_budgets()


def get_credit_score(email, password):
    mint = Mint(email, password)
    return mint.get_credit_score()


def get_credit_report(email, password):
    mint = Mint(email, password)
    return mint.get_credit_report()


def initiate_account_refresh(email, password):
    mint = Mint(email, password)
    return mint.initiate_account_refresh()

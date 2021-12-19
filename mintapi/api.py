from datetime import date, datetime, timedelta
import io
import json
import logging
import os
import random
import re
import requests
import time
import warnings

import xmltodict
import pandas as pd

from mintapi.signIn import sign_in, _create_web_driver_at_mint_com


logger = logging.getLogger("mintapi")


def json_date_to_datetime(dateraw):
    cy = date.today().year
    try:
        newdate = datetime.strptime(dateraw + str(cy), "%b %d%Y")
    except ValueError:
        newdate = convert_mmddyy_to_datetime(dateraw)
    return newdate


def convert_mmddyy_to_datetime(date):
    try:
        newdate = datetime.strptime(date, "%m/%d/%y")
    except (TypeError, ValueError):
        newdate = None
    return newdate


def convert_date_to_string(date):
    date_string = None
    if date:
        date_string = date.strftime("%m/%d/%Y")
    return date_string


def reverse_credit_amount(row):
    amount = float(row["amount"][1:].replace(",", ""))
    return amount if row["isDebit"] else -amount


IGNORE_FLOAT_REGEX = re.compile(r"[$,%]")


def parse_float(str_number):
    try:
        return float(IGNORE_FLOAT_REGEX.sub("", str_number))
    except ValueError:
        return None


DATE_FIELDS = [
    "addAccountDate",
    "closeDate",
    "fiLastUpdated",
    "lastUpdated",
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
            account[df + "InDate"] = datetime.fromtimestamp(ts)


MINT_ROOT_URL = "https://mint.intuit.com"
MINT_ACCOUNTS_URL = "https://accounts.intuit.com"
MINT_CREDIT_URL = "https://credit.finance.intuit.com"

JSON_HEADER = {"accept": "application/json"}


class MintException(Exception):
    pass


class Mint(object):
    request_id = 42  # magic number? random number?
    token = None
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
        use_chromedriver_on_path=False,
        chromedriver_download_path=os.getcwd(),
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
                use_chromedriver_on_path=use_chromedriver_on_path,
                chromedriver_download_path=chromedriver_download_path,
            )

    @classmethod
    def get_rnd(cls):  # {{{
        return str(int(time.mktime(datetime.now().timetuple()))) + str(
            random.randrange(999)
        ).zfill(3)

    def _get_api_key_header(self):
        key_var = "window.MintConfig.browserAuthAPIKey"
        api_key = self.driver.execute_script("return " + key_var)
        auth = "Intuit_APIKey intuit_apikey=" + api_key
        auth += ", intuit_apikey_version=1.0"
        header = {"authorization": auth}
        header.update(JSON_HEADER)
        return header

    def close(self):
        """Logs out and quits the current web driver/selenium session."""
        if not self.driver:
            return

        self.driver.quit()
        self.driver = None

    def request_and_check(
        self, url, method="get", expected_content_type=None, **kwargs
    ):
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
        assert method in ["get", "post"]
        result = self.driver.request(method, url, **kwargs)
        if result.status_code != requests.codes.ok:
            raise RuntimeError(
                "Error requesting %r, status = %d" % (url, result.status_code)
            )
        if expected_content_type is not None:
            content_type = result.headers.get("content-type", "")
            if not re.match(expected_content_type, content_type):
                raise RuntimeError(
                    "Error requesting %r, content type %r does not match %r"
                    % (url, content_type, expected_content_type)
                )
        return result

    def get(self, url, **kwargs):
        return self.driver.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.driver.request("POST", url, **kwargs)

    def make_post_request(self, url, data, convert_to_text=False):
        response = self.post(url=url, data=data, headers=JSON_HEADER)
        if convert_to_text:
            response = response.text
        return response

    def build_bundledServiceController_url(self):
        return "{}/bundledServiceController.xevent?legacy=false&token={}".format(
            MINT_ROOT_URL, self.token
        )

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
        use_chromedriver_on_path=False,
        chromedriver_download_path=os.getcwd(),
    ):

        self.driver = _create_web_driver_at_mint_com(
            headless, session_path, use_chromedriver_on_path, chromedriver_download_path
        )

        try:
            self.status_message, self.token = sign_in(
                email,
                password,
                self.driver,
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
            self.driver.quit()

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
            "{}/bps/v2/payer/bills".format(MINT_ROOT_URL),
            headers=self._get_api_key_header(),
        ).json()["bills"]

    def get_invests_json(self):
        warnings.warn(
            "We will deprecate get_invests_json method in the next major release due to an updated endpoint for"
            "investment data.  Transition to use the updated get_investment_data method, which is also now accessible via command-line.",
            DeprecationWarning,
        )
        body = self.get(
            "{}/investment.event".format(MINT_ROOT_URL),
        ).text
        p = re.search(
            r'<input name="json-import-node" type="hidden" value="json = ([^"]*);"',
            body,
        )
        if p:
            return p.group(1).replace("&quot;", '"')
        else:
            logger.error("FAIL2")

    def get_investment_data(self):
        investments = self.__call_investments_endpoint()
        if "Investment" in investments.keys():
            for i in investments["Investment"]:
                i["lastUpdatedDate"] = i["metaData"]["lastUpdatedDate"]
                i.pop("metaData", None)
        else:
            raise MintException("Cannot find investment data")
        return investments["Investment"]

    def __call_investments_endpoint(self):
        return self.get(
            "{}/pfm/v1/investments".format(MINT_ROOT_URL),
            headers=self._get_api_key_header(),
        ).json()

    def get_categories(self):
        return self.get(
            "{}/pfm/v1/categories".format(MINT_ROOT_URL),
            headers=self._get_api_key_header(),
        ).json()["Category"]

    def get_accounts(self, get_detail=False):  # {{{
        # Issue service request.
        req_id = self.get_request_id_str()

        input = {
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
                    "UNCLASSIFIED",
                ]
            },
            "id": req_id,
            "service": "MintAccountService",
            "task": "getAccountsSorted"
            # 'task': 'getAccountsSortedByBalanceDescending'
        }

        data = {"input": json.dumps([input])}
        response = self.make_post_request(
            url=self.build_bundledServiceController_url(),
            data=data,
            convert_to_text=True,
        )
        if req_id not in response:
            raise MintException("Could not parse account data: " + response)

        # Parse the request
        response = json.loads(response)
        accounts = response["response"][req_id]["response"]

        for account in accounts:
            convert_account_dates_to_datetime(account)

        if get_detail:
            accounts = self.populate_extended_account_detail(accounts)

        return accounts

    def set_user_property(self, name, value):
        req_id = self.get_request_id_str()
        data = {
            "input": json.dumps(
                [
                    {
                        "args": {"propertyName": name, "propertyValue": value},
                        "service": "MintUserService",
                        "task": "setUserProperty",
                        "id": req_id,
                    }
                ]
            )
        }
        result = self.make_post_request(
            url=self.build_bundledServiceController_url(), data=data
        )
        if result.status_code != 200:
            raise MintException("Received HTTP error %d" % result.status_code)
        response = result.text
        if req_id not in response:
            raise MintException("Could not parse response to set_user_property")

    def get_transactions_json(
        self,
        include_investment=False,
        skip_duplicates=False,
        start_date=None,
        end_date=None,
        id=0,
    ):
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
        self.set_user_property("hide_duplicates", "T" if skip_duplicates else "F")

        # Converts the start date into datetime format - input must be mm/dd/yy
        start_date = convert_mmddyy_to_datetime(start_date)
        # Converts the end date into datetime format - input must be mm/dd/yy
        end_date = convert_mmddyy_to_datetime(end_date)

        all_txns = []
        offset = 0
        # Mint only returns some of the transactions at once.  To get all of
        # them, we have to keep asking for more until we reach the end.
        while 1:
            url = MINT_ROOT_URL + "/getJsonData.xevent"
            params = {
                "queryNew": "",
                "offset": offset,
                "comparableType": "8",
                "startDate": convert_date_to_string(start_date),
                "endDate": convert_date_to_string(end_date),
                "rnd": Mint.get_rnd(),
            }
            # Specifying accountId=0 causes Mint to return investment
            # transactions as well.  Otherwise they are skipped by
            # default.
            if id > 0 or include_investment:
                params["accountId"] = id
            if include_investment:
                params["task"] = "transactions"
            else:
                params["task"] = "transactions,txnfilters"
                params["filterType"] = "cash"
            result = self.request_and_check(
                url,
                headers=JSON_HEADER,
                params=params,
                expected_content_type="text/json|application/json",
            )
            data = json.loads(result.text)
            txns = data["set"][0].get("data", [])
            if not txns:
                break
            all_txns.extend(txns)
            offset += len(txns)
        return all_txns

    def get_detailed_transactions(
        self,
        include_investment=False,
        skip_duplicates=False,
        remove_pending=True,
        start_date=None,
        end_date=None,
    ):
        """Returns the JSON transaction data as a DataFrame, and converts
        current year dates and prior year dates into consistent datetime
        format, and reverses credit activity.

        Note: start_date and end_date must be in format mm/dd/yy.
        If pulls take too long, consider a narrower range of start and end
        date. See json explanations of include_investment and skip_duplicates.

        Also note: Mint includes pending transactions, however these sometimes
        change dates/amounts after the transactions post. They have been
        removed by default in this pull, but can be included by changing
        remove_pending to False

        """
        result = self.get_transactions_json(
            include_investment, skip_duplicates, start_date, end_date
        )

        df = pd.DataFrame(self.add_parent_category_to_result(result))
        df["odate"] = df["odate"].apply(json_date_to_datetime)

        if remove_pending:
            df = df[~df.isPending]
            df.reset_index(drop=True, inplace=True)

        df.amount = df.apply(reverse_credit_amount, axis=1)

        return df

    def add_parent_category_to_result(self, result):
        # Finds the parent category name from the categories object based on
        # the transaction category ID
        categories = self.get_categories()
        for transaction in result:
            category = self.get_category_object_from_id(
                transaction["categoryId"], categories
            )
            parent = self._find_parent_from_category(category, categories)
            transaction["parentCategoryId"] = self.__format_category_id(parent["id"])
            transaction["parentCategoryName"] = parent["name"]

        return result

    def get_transactions_csv(
        self, include_investment=False, start_date=None, end_date=None, acct=0
    ):
        """Returns the raw CSV transaction data as downloaded from Mint.

        If include_investment == True, also includes transactions that Mint
        classifies as investment-related.  You may find that the investment
        transaction data is not sufficiently detailed to actually be useful,
        however.
        """

        # Specifying accountId=0 causes Mint to return investment
        # transactions as well.  Otherwise they are skipped by
        # default.

        params = {
            "accountId": acct if acct > 0 else None,
            "startDate": convert_date_to_string(convert_mmddyy_to_datetime(start_date)),
            "endDate": convert_date_to_string(convert_mmddyy_to_datetime(end_date)),
        }
        result = self.request_and_check(
            "{}/transactionDownload.event".format(MINT_ROOT_URL),
            params=params,
            expected_content_type="text/csv",
        )
        return result.content

    def get_net_worth(self, account_data=None):
        if account_data is None:
            account_data = self.get_accounts()

        # account types in this list will be subtracted
        invert = set(["loan", "loans", "credit"])
        return sum(
            [
                -a["currentBalance"]
                if a["accountType"] in invert
                else a["currentBalance"]
                for a in account_data
                if a["isActive"]
            ]
        )

    def get_transactions(
        self, include_investment=False, start_date=None, end_date=None
    ):
        """Returns the transaction data as a Pandas DataFrame."""
        s = io.BytesIO(
            self.get_transactions_csv(
                start_date=start_date,
                end_date=end_date,
                include_investment=include_investment,
            )
        )
        s.seek(0)
        df = pd.read_csv(s, parse_dates=["Date"])
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df.category = df.category.str.lower().replace("uncategorized", pd.NA)
        return df

    def populate_extended_account_detail(self, accounts):  # {{{
        # I can't find any way to retrieve this information other than by
        # doing this stupid one-call-per-account to listTransactions.xevent
        # and parsing the HTML snippet :(
        for account in accounts:
            headers = dict(JSON_HEADER)
            headers["Referer"] = "{}/transaction.event?accountId={}".format(
                MINT_ROOT_URL, account["id"]
            )

            list_txn_url = "{}/listTransaction.xevent".format(MINT_ROOT_URL)
            params = {
                "accountId": str(account["id"]),
                "queryNew": "",
                "offset": 0,
                "comparableType": 8,
                "acctChanged": "T",
                "rnd": Mint.get_rnd(),
            }

            response = json.loads(
                self.get(list_txn_url, params=params, headers=headers).text
            )
            xml = "<div>" + response["accountHeader"] + "</div>"
            xml = xml.replace("&#8211;", "-")
            xml = xmltodict.parse(xml)

            account["availableMoney"] = None
            account["totalFees"] = None
            account["totalCredit"] = None
            account["nextPaymentAmount"] = None
            account["nextPaymentDate"] = None

            xml = xml["div"]["div"][1]["table"]
            if "tbody" not in xml:
                continue
            xml = xml["tbody"]
            table_type = xml["@id"]
            xml = xml["tr"][1]["td"]

            if table_type == "account-table-bank":
                account["availableMoney"] = parse_float(xml[1]["#text"])
                account["totalFees"] = parse_float(xml[3]["a"]["#text"])
                if account["interestRate"] is None:
                    account["interestRate"] = parse_float(xml[2]["#text"]) / 100.0
            elif table_type == "account-table-credit":
                account["availableMoney"] = parse_float(xml[1]["#text"])
                account["totalCredit"] = parse_float(xml[2]["#text"])
                account["totalFees"] = parse_float(xml[4]["a"]["#text"])
                if account["interestRate"] is None:
                    account["interestRate"] = parse_float(xml[3]["#text"]) / 100.0
            elif table_type == "account-table-loan":
                account["nextPaymentAmount"] = parse_float(xml[1]["#text"])
                account["nextPaymentDate"] = xml[2].get("#text", None)
            elif table_type == "account-type-investment":
                account["totalFees"] = parse_float(xml[2]["a"]["#text"])

        return accounts

    def get_budgets(self, hist=None):
        response = self.__call_budgets_endpoint()
        categories = self.get_categories()
        income = response["data"]["income"]
        spending = response["data"]["spending"]
        if hist is not None:  # version proofing api

            def mos_to_yrmo(mos_frm_zero):
                return datetime(
                    year=int(mos_frm_zero / 12), month=mos_frm_zero % 12 + 1, day=1
                ).strftime("%Y%m")

            # Error checking 'hist' argument
            if isinstance(hist, str) or hist > 12:
                hist = 12  # MINT_ROOT_URL only calls last 12 months of budget data
            elif hist < 1:
                hist = 1

            bgt_cur_mo = max(map(int, income.keys()))
            min_mo_hist = bgt_cur_mo - hist

            # Initialize and populate dictionary for return
            #   Output 'budgets' dictionary with structure
            #       { "YYYYMM": {"spending": [{"key": value, ...}, ...],
            #                      "income": [{"key": value, ...}, ...] } }
            budgets = {}
            for months in range(bgt_cur_mo, min_mo_hist, -1):
                budgets[mos_to_yrmo(months)] = {}
                budgets[mos_to_yrmo(months)]["income"] = income[str(months)]["bu"]
                budgets[mos_to_yrmo(months)]["spending"] = spending[str(months)]["bu"]

            # Fill in the return structure
            for month in budgets.keys():
                for direction in budgets[month]:
                    for budget in budgets[month][direction]:
                        budget = self.__format_budget_categories(budget, categories)

        else:
            # Make the skeleton return structure
            budgets = {
                "income": income[str(max(map(int, income.keys())))]["bu"],
                "spend": spending[str(max(map(int, spending.keys())))]["bu"],
            }

            # Fill in the return structure
            for direction in budgets.keys():
                for budget in budgets[direction]:
                    budget = self.__format_budget_categories(budget, categories)

        return budgets

    def __call_budgets_endpoint(self):
        # Issue request for budget utilization
        first_of_this_month = date.today().replace(day=1)
        eleven_months_ago = (first_of_this_month - timedelta(days=330)).replace(day=1)
        url = "{}/getBudget.xevent".format(MINT_ROOT_URL)
        params = {
            "startDate": convert_date_to_string(eleven_months_ago),
            "endDate": convert_date_to_string(first_of_this_month),
            "rnd": Mint.get_rnd(),
        }
        return json.loads(self.get(url, params=params, headers=JSON_HEADER).text)

    def __format_budget_categories(self, budget, categories):
        category = self.get_category_object_from_id(budget["cat"], categories)
        budget["cat"] = category["name"]
        parent = self._find_parent_from_category(category, categories)
        budget["parent"] = parent["name"]
        return budget

    def get_category_object_from_id(self, cid, categories):
        if cid == 0:
            return {"parent": "Uncategorized", "depth": 1, "name": "Uncategorized"}

        result = filter(
            lambda category: self.__format_category_id(category["id"]) == str(cid),
            categories,
        )
        category = list(result)
        return (
            category[0]
            if len(category) > 0
            else {"parent": "Unknown", "depth": 1, "name": "Unknown"}
        )

    def __format_category_id(self, cid):
        return cid if str(cid).find("_") == "-1" else str(cid)[str(cid).find("_") + 1 :]

    def _find_parent_from_category(self, category, categories):
        if category["depth"] == 1:
            return {"id": "", "name": ""}

        parent = self.get_category_object_from_id(
            self.__format_category_id(category["parentId"]), categories
        )
        return {"id": parent["id"], "name": parent["name"]}

    def initiate_account_refresh(self):
        data = {"token": self.token}
        self.make_post_request(
            url="{}/refreshFILogins.xevent".format(MINT_ROOT_URL), data=data
        )

    def get_credit_score(self):
        # Request a single credit report, and extract the score
        report = self.get_credit_report(
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

    def get_credit_report(
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
        return self.driver.get(MINT_CREDIT_URL)

    def _get_credit_reports(self, limit, credit_header):
        return self.get(
            "{}/v1/creditreports?limit={}".format(MINT_CREDIT_URL, limit),
            headers=credit_header,
        ).json()

    def _get_credit_details(self, url, credit_header):
        return self.get(url.format(MINT_CREDIT_URL), headers=credit_header).json()

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


def get_accounts(email, password, get_detail=False):
    mint = Mint(email, password)
    return mint.get_accounts(get_detail=get_detail)


def get_net_worth(email, password):
    mint = Mint(email, password)
    account_data = mint.get_accounts()
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


if __name__ == "__main__":
    warnings.warn(
        "Calling command line code from api.py will be deprecated in a future release.\n"
        "Please call mintapi directly. For examples, see the README.md",
        DeprecationWarning,
    )
    from mintapi.cli import main

    main()

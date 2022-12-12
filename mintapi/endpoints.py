"""
Shared Endpoint module to keep definitions independent of implementation
(browser vs REST)
"""


import logging
from abc import ABCMeta, abstractmethod
from datetime import datetime
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

import pandas as pd
from mintapi.constants import MINT_CREDIT_URL, MINT_ROOT_URL
from mintapi.filters import DateFilter, SearchFilterBuilder
from mintapi.transactions import TransactionRequest
from mintapi.trends import ReportView, TrendRequest
from requests import Response

LOGGER = logging.getLogger(__name__)


class MintEndpoints(object, metaclass=ABCMeta):
    """
    Mixin class with endpoint routes
    Expects implementing class to define the request method
    """

    @abstractmethod
    def request(self):
        pass

    def get(self, **kwargs):
        return self.request(method="GET", **kwargs)

    def post(self, **kwargs):
        return self.request(method="POST", **kwargs)

    def _paginate(self, data_key: str, metadata_key: str, response: Response, **kwargs):
        """
        Mint API appears to use a limit-offset pagination mechanism with
        href links embedded in responses. Can iterate through sequentially
        and append results together

        Data schema:
        {DataType: [], metaData: {}} where DataType is a dynamic key mapping to the endpoint
        metaData follows a consistent format:

        {
            'asOf': 'TIMESTAMP',
            'totalSize': INT,
            'pageSize': 20,
            'currentPage': 1,
            'offset': 0,
            'limit': 20,
            'link': [
                {'otherAttributes': {'method': 'GET'}, 'href': '/v1/accounts', 'rel': 'self'},
                {'otherAttributes': {}, 'href': '/v1/accounts?offset=20&limit=20', 'rel': 'next'}
            ]
        }

        Parameters
        ----------
        data_key : str
            _description_
        response : Response
            _description_

        Returns
        -------
        _type_
            _description_
        """
        data = []

        json_data = response.json()

        # early abort if no data extraction theme
        if data_key is None or data_key not in json_data:
            LOGGER.warning("Data key not in response data, returning empty list")
            LOGGER.debug(json_data)
            return data

        data.extend(json_data[data_key])

        # early abort if no pagination mechanism defined
        if metadata_key is None or metadata_key not in json_data:
            if metadata_key is not None:
                LOGGER.warning("Metadata key not in response data, not iterating")
            return data

        metadata = _ResponseMetadata(json_data[metadata_key], **kwargs)

        while metadata.has_next:
            response = self.request(
                uri_path=metadata.next_uri_path,
                data_key=data_key,
                metadata_key=metadata_key,
                paginate=False,
                **metadata.next_kwargs,
            )
            json_data = response.json()
            data.extend(json_data[data_key])
            metadata = _ResponseMetadata(
                json_data[metadata_key], **metadata.next_kwargs
            )

        return data

    """
    Endpoints - Acts as the api descriptor (equivalent to an openapi generated client)
    Separates out endpoint info to make future updates easy without changing the publicly
    exposed methods
    """

    def _initiate_account_refresh(self, **kwargs):
        api_url = MINT_ROOT_URL
        api_section = ""
        uri_path = "/refreshFILogins.xevent"
        metadata_key = None
        data_key = None

        return self.post(
            api_url=api_url,
            api_section=api_section,
            uri_path=uri_path,
            data_key=data_key,
            metadata_key=metadata_key,
            **kwargs,
        )

    def _get_account_data(self, **kwargs):
        api_url = MINT_ROOT_URL
        api_section = "/pfm"
        uri_path = "/v1/accounts"
        metadata_key = "metaData"
        data_key = "Account"

        return self.get(
            api_url=api_url,
            api_section=api_section,
            uri_path=uri_path,
            data_key=data_key,
            metadata_key=metadata_key,
            **kwargs,
        )

    def _get_budget_data(self, **kwargs):
        api_url = MINT_ROOT_URL
        api_section = "/pfm"
        uri_path = "/v1/budgets"
        metadata_key = "metaData"
        data_key = "Budget"

        return self.get(
            api_url=api_url,
            api_section=api_section,
            uri_path=uri_path,
            data_key=data_key,
            metadata_key=metadata_key,
            **kwargs,
        )

    def _get_bills_data(self, **kwargs):
        api_url = MINT_ROOT_URL
        api_section = "/bps"
        uri_path = "/v2/payer/bills"
        metadata_key = "collectionMetaData"
        data_key = "bills"

        return self.get(
            api_url=api_url,
            api_section=api_section,
            uri_path=uri_path,
            data_key=data_key,
            metadata_key=metadata_key,
            **kwargs,
        )

    def _get_category_data(self, **kwargs):
        api_url = MINT_ROOT_URL
        api_section = "/pfm"
        uri_path = "/v1/categories"
        metadata_key = "metaData"
        data_key = "Category"

        return self.get(
            api_url=api_url,
            api_section=api_section,
            uri_path=uri_path,
            data_key=data_key,
            metadata_key=metadata_key,
            **kwargs,
        )

    def _get_credit_accounts(self, **kwargs):
        api_url = MINT_CREDIT_URL
        api_section = ""
        uri_path = "/v1/creditreports/0/tradelines"
        metadata_key = None
        data_key = None

        return self.get(
            api_url=api_url,
            api_section=api_section,
            uri_path=uri_path,
            data_key=data_key,
            metadata_key=metadata_key,
            **kwargs,
        )

    def _get_credit_inquiries(self, **kwargs):
        api_url = MINT_CREDIT_URL
        api_section = ""
        uri_path = "/v1/creditreports/0/inquiries"
        metadata_key = None
        data_key = None

        return self.get(
            api_url=api_url,
            api_section=api_section,
            uri_path=uri_path,
            data_key=data_key,
            metadata_key=metadata_key,
            **kwargs,
        )

    def _get_credit_reports(self, **kwargs):
        api_url = MINT_CREDIT_URL
        api_section = ""
        uri_path = "/v1/creditreports"
        metadata_key = None
        data_key = None

        return self.get(
            api_url=api_url,
            api_section=api_section,
            uri_path=uri_path,
            data_key=data_key,
            metadata_key=metadata_key,
            **kwargs,
        )

    def _get_credit_utilization(self, **kwargs):
        api_url = MINT_CREDIT_URL
        api_section = ""
        uri_path = "/v1/creditreports/creditutilizationhistory"
        metadata_key = None
        data_key = None

        return self.get(
            api_url=api_url,
            api_section=api_section,
            uri_path=uri_path,
            data_key=data_key,
            metadata_key=metadata_key,
            **kwargs,
        )

    def _get_investment_data(self, **kwargs):
        api_url = MINT_ROOT_URL
        api_section = "/pfm"
        uri_path = "/v1/investments"
        metadata_key = "metaData"
        data_key = "Investment"

        return self.get(
            api_url=api_url,
            api_section=api_section,
            uri_path=uri_path,
            data_key=data_key,
            metadata_key=metadata_key,
            **kwargs,
        )

    def _get_transaction_data(self, **kwargs):
        api_url = MINT_ROOT_URL
        api_section = "/pfm"
        uri_path = "/v1/transactions/search"
        metadata_key = "metaData"
        data_key = "Transaction"

        return self.post(
            api_url=api_url,
            api_section=api_section,
            uri_path=uri_path,
            data_key=data_key,
            metadata_key=metadata_key,
            **kwargs,
        )

    def _get_trend_data(self, **kwargs):
        api_url = MINT_ROOT_URL
        api_section = "/pfm"
        uri_path = "/v1/trends"
        metadata_key = "metaData"
        data_key = "Trend"

        return self.post(
            api_url=api_url,
            api_section=api_section,
            uri_path=uri_path,
            data_key=data_key,
            metadata_key=metadata_key,
            **kwargs,
        )

    """
    User Methods - Add custom postprocessing logic here
    """

    def initiate_account_refresh(self):
        """
        _summary_
        """

        self._initiate_account_refresh()

    def get_account_data(self, limit: int = 1000, **kwargs):
        """
        _summary_

        Parameters
        ----------
        limit : int, optional
            _description_, by default 1000

        Returns
        -------
        _type_
            _description_
        """
        params = {
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return self._get_account_data(params=params, **kwargs)

    def get_bills_data(self, **kwargs):
        """
        _summary_

        Returns
        -------
        _type_
            _description_
        """
        return self._get_bills_data(**kwargs)

    def get_budget_data(
        self, start_date: str = None, end_date: str = None, limit: int = 1000, **kwargs
    ):
        """
        _summary_

        Parameters
        ----------
        start_date : str, optional
            _description_, by default None
        end_date : str, optional
            _description_, by default None
        limit : int, optional
            _description_, by default 1000

        Returns
        -------
        _type_
            _description_
        """
        params = {
            "startDate": start_date,
            "endDate": end_date,
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return self._get_budget_data(params=params, **kwargs)

    def get_category_data(self, limit: int = 1000, **kwargs):
        """
        _summary_

        Parameters
        ----------
        limit : int, optional
            _description_, by default 1000

        Returns
        -------
        _type_
            _description_
        """
        params = {
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return self._get_category_data(params=params, **kwargs)

    def get_credit_accounts(self, **kwargs):
        """
        _summary_

        Returns
        -------
        _type_
            _description_
        """
        return self._get_credit_accounts(**kwargs)

    def get_credit_inquiries(self, **kwargs):
        """
        _summary_

        Returns
        -------
        _type_
            _description_
        """
        return self._get_credit_inquiries(**kwargs)

    def get_credit_reports(self, limit: int = 1000, **kwargs):
        """
        _summary_

        Parameters
        ----------
        limit : int, optional
            _description_, by default 1000

        Returns
        -------
        _type_
            _description_
        """
        params = {
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return self._get_credit_reports(params=params, **kwargs)

    def get_credit_utilization(self, **kwargs):
        """
        _summary_

        Returns
        -------
        _type_
            _description_
        """

        def _process_utilization(data):
            # Function to clean up the credit utilization history data
            utilization = []
            utilization.extend(_flatten_utilization(data["cumulative"]))
            for trade in data["tradelines"]:
                utilization.extend(_flatten_utilization(trade))
            return utilization

        def _flatten_utilization(data):
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

        data = self._get_credit_utilization(**kwargs)
        return _process_utilization(data)

    def get_investment_data(self, limit: int = 1000, **kwargs):
        """
        _summary_

        Parameters
        ----------
        limit : int, optional
            _description_, by default 1000

        Returns
        -------
        _type_
            _description_
        """
        params = {
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return self._get_investment_data(params=params, **kwargs)

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
        limit: int = 1000,
        offset: int = 0,
        **kwargs
    ):
        """
        Public accessor for transaction data. Internally constructs a transaction/search api payload

        Also note: Mint includes pending transactions, however these sometimes
        change dates/amounts after the transactions post. They have been
        removed by default in this pull, but can be included by changing
        remove_pending to False

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
            page size, by default 1000
        offset : int, optional
            offset pagination for next pages, by default 0

        Returns
        -------
        List[Dict]
            returns a list of transaction results (each dict)
        """

        search_filter = SearchFilterBuilder.search_builder(
            match_all_filters=match_all_filters,
            category_ids=category_ids,
            tag_ids=tag_ids,
            descriptions=descriptions,
            account_ids=account_ids,
        )

        payload = TransactionRequest(
            date_filter=DateFilter(
                date_filter=date_filter, start_date=start_date, end_date=end_date
            ),
            search_filters=search_filter,
            limit=limit,
            offset=offset,
        )

        data = self._get_transaction_data(json=payload.to_dict(), **kwargs)

        if remove_pending:
            filtered = filter(
                lambda transaction: transaction["isPending"] is False,
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

    def get_trend_data(
        self,
        report_type: ReportView.Options = ReportView.Options.SPENDING_TIME,
        date_filter: DateFilter.Options = DateFilter.Options.THIS_MONTH,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        account_ids: List[str] = None,
        category_ids: List[str] = None,
        tag_ids: List[str] = None,
        descriptions: List[str] = None,
        match_all_filters: bool = True,
        limit: int = 1000,
        offset: int = 0,
        **kwargs
    ):
        """
        Public accessor for trend data. Internally constructs a trend api payload


        Parameters
        ----------
        report_type : ReportView.Options
            type of report to generate. must use one of enum values
        date_filter : DateFilter.Options
            date window. must use predefined enum windows or pass a start and end date with CUSTOM enum
        start_date : Optional[str], optional
            optional start date (YYYY-mm-dd) if using enum CUSTOM, by default None
        end_date : Optional[str], optional
            optional end date (YYYY-mm-dd) if using enum CUSTOM, by default None
        account_ids : List[str], optional
            optional list of account ids to filter by, by default None
        category_ids : List[str], optional
            optional list of category ids to filter by, by default None
        tag_ids : List[str], optional
            optional list of tag ids to filter by, by default None
        descriptions : List[str], optional
            optional list of descriptions (ui labeled merchants) to filter by, by default None
        match_all_filters : bool, optional
            whether to match all (True) supplied filters or any (False), by default True
        limit : int, optional
            page size, by default 1000
        offset : int, optional
            offset pagination for next pages, by default 0

        Returns
        -------
        List[Dict]
            returns a list of trend results (each dict)
        """
        search_filter = SearchFilterBuilder.search_builder(
            match_all_filters=match_all_filters,
            category_ids=category_ids,
            tag_ids=tag_ids,
            descriptions=descriptions,
            account_ids=account_ids,
        )

        payload = TrendRequest(
            report_view=ReportView(report_type=report_type),
            date_filter=DateFilter(
                date_filter=date_filter, start_date=start_date, end_date=end_date
            ),
            search_filters=search_filter,
            limit=limit,
            offset=offset,
        )

        return self._get_trend_data(json=payload.to_dict(), **kwargs)

    """
    Convenience wrappers
    """

    def get_net_worth_data(self):
        """
        Trend API convenience wrapper to sum accounts for each time period
        """
        data = self.get_trend_data(
            report_type=ReportView.Options.NET_WORTH,
            date_filter=DateFilter.Options.ALL_TIME,
        )

        # returns record for ASSET and DEBT for each time period. Merge and diff for actual net
        assets = [i for i in data if i["type"] == "ASSET"]
        debts = [i for i in data if i["type"] == "DEBT"]

        asset_df = pd.DataFrame(assets)[["date", "amount"]].rename(
            columns={"amount": "assets"}
        )
        debts_df = pd.DataFrame(debts)[["date", "amount"]].rename(
            columns={"amount": "debts"}
        )
        # invert debts
        debts_df["debts"] = -1 * debts_df["debts"]

        merged = asset_df.merge(debts_df, how="outer", on=["date"])
        merged["net"] = merged["assets"] + merged["debts"]

        return merged.to_dict("records")

    def get_credit_report_data(
        self,
        limit=2,
        details=True,
        exclude_inquiries=False,
        exclude_accounts=False,
        exclude_utilization=False,
    ):
        # Get credit reports. The UI shows 2 by default, but more are available!
        # At least 8, but could be all the TransUnion reports Mint has
        # How the "bands" are defined, and other metadata, is available at a
        # /v1/creditscoreproviders/3 endpoint (3 = TransUnion)
        credit_report = dict()
        credit_report["reports"] = self.get_credit_reports(limit=limit)

        # If we want details, request the detailed sub-reports
        if details:
            # Get full list of credit inquiries
            if not exclude_inquiries:
                credit_report["inquiries"] = self.get_credit_inquiries()

            # Get full list of credit accounts
            if not exclude_accounts:
                credit_report["accounts"] = self.get_credit_accounts()

            # Get credit utilization history (~3 months, by account)
            if not exclude_utilization:
                credit_report["utilization"] = self.get_credit_utilization()

        return credit_report

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

    def get_account_balance_history(self):
        """
        Convenience wrapper to iterate through all accounts and get trend data
        by account

        Returns
        -------
        _type_
            _description_
        """
        # Account Balance history by account
        balances = []

        accounts = self.get_account_data()
        for account in accounts:
            account_id = account["id"]
            # try extracting as asset and debt
            for report in (
                ReportView.Options.ASSETS_TIME,
                ReportView.Options.DEBTS_TIME,
            ):
                data = self.get_trend_data(
                    report_type=report,
                    date_filter=DateFilter.Options.ALL_TIME,
                    account_ids=[account_id],
                )
                for d in data:
                    d["account_id"] = account_id
                balances.extend(data)
        return balances


class _ResponseMetadata(object):
    """
    Convenience wrapper for pagination
    """

    def __init__(self, metadata, **kwargs):
        self.metadata = metadata
        self.kwargs = kwargs

    @property
    def has_next(self):
        return "link" in self.metadata and any(
            [i["rel"] == "next" for i in self.metadata["link"]]
        )

    @property
    def next_uri_path(self):
        link = [i for i in self.metadata["link"] if i["rel"] == "next"][0]
        return link["href"]

    @property
    def next_kwargs(self):
        """
        manage param changes between requests - necessary for post requests
        with fixed limits/offsets
        """
        # drop url params from propagating (href includes the full uri path already)
        new_kwargs = {k: v for k, v in self.kwargs.items() if k != "params"}

        if new_kwargs["method"] == "POST":
            # api returns next uri but we have to match payload params
            next_uri = self.next_uri_path
            params = parse_qs(urlparse(next_uri).query)
            if "offset" in params and "json" in new_kwargs:
                new_kwargs["json"]["offset"] = params["offset"][0]
            if "limit" in params and "json" in new_kwargs:
                new_kwargs["json"]["limit"] = params["limit"][0]

        return new_kwargs

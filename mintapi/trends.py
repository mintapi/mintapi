"""
Trends helper classes
"""

from dataclasses import dataclass
from enum import Enum
from typing import Union
from mintapi.filters import SearchFilter, DateFilter


@dataclass
class ReportView:
    class Options(Enum):
        """
        Report Types were inspected from the UI by clicking through all the available views
        """

        SPENDING_TIME = 1
        SPENDING_CATEGORY = 2
        SPENDING_MERCHANT = 3
        SPENDING_TAG = 4

        INCOME_TIME = 5
        INCOME_CATEGORY = 6
        INCOME_MERCHANT = 7
        INCOME_TAG = 8

        ASSETS_TYPE = 9
        ASSETS_TIME = 10
        ASSETS_ACCOUNT = 11

        DEBTS_TIME = 12
        DEBTS_TYPE = 13
        DEBTS_ACCOUNT = 14

        NET_WORTH = 15
        NET_INCOME = 16

    report_type: Union[Options, str]

    def __post_init__(self):
        if isinstance(self.report_type, str):
            assert hasattr(self.Options, self.report_type)
        elif isinstance(self.report_type, self.Options):
            self.report_type = self.report_type.name
        else:
            raise ValueError(
                "Report Type must be one of allowed values in enum `ReportView.Options"
            )

    def to_dict(self):
        return {"reportView": {"type": self.report_type}}


@dataclass
class TrendRequest:
    """
    Helper class to construct a trend request payload

    Parameters
    ----------
    object : _type_
        _description_
    """

    date_filter: DateFilter
    search_filters: SearchFilter
    report_view: ReportView
    limit: int = 5000
    offset: int = 0

    def to_dict(self):
        return {
            **self.report_view.to_dict(),
            **self.date_filter.to_dict(),
            **self.search_filters.to_dict(),
            "limit": self.limit,
            "offset": self.offset,
        }

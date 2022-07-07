"""
Trends helper classes
"""

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Union


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
class DateFilter:
    class Options(Enum):
        """
        Date options were inspected from the UI by clicking through all the available views
        """

        LAST_7_DAYS = 1
        LAST_14_DAYS = 2
        THIS_MONTH = 3
        LAST_MONTH = 4
        LAST_3_MONTHS = 5
        LAST_6_MONTHS = 6
        LAST_12_MONTHS = 7
        THIS_YEAR = 8
        LAST_YEAR = 9
        ALL_TIME = 10
        CUSTOM = 11

    date_filter: Union[Options, str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.date_filter, str):
            assert hasattr(self.Options, self.date_filter)
        elif isinstance(self.date_filter, self.Options):
            self.date_filter = self.date_filter.name
        else:
            raise ValueError(
                "Date Filter must be one of allowed values in enum `DateFilter.Options"
            )

        if self.date_filter == self.Options.CUSTOM.name:
            # validate required start and end dates
            assert self.start_date is not None
            assert self.end_date is not None

    def to_dict(self):
        filter_clause = {"dateFilter": {"type": self.date_filter}}
        if self.date_filter == self.Options.CUSTOM.name:
            filter_clause["dateFilter"]["startDate"] = self.start_date
            filter_clause["dateFilter"]["endDate"] = self.end_date
        return filter_clause


@dataclass
class MatchFilter(metaclass=ABCMeta):
    @abstractmethod
    def to_dict(self):
        pass


@dataclass
class CategoryMatchFilter(MatchFilter):
    category_id: str
    include_child_categories: bool

    def to_dict(self):
        return {
            "type": "CategoryIdFilter",
            "categoryId": self.category_id,
            "includeChildCategories": self.include_child_categories,
        }


@dataclass
class DescriptionMatchFilter(MatchFilter):
    description: str

    def to_dict(self):
        return {"type": "DescriptionNameFilter", "description": self.description}


@dataclass
class TagMatchFilter(MatchFilter):
    tag_id: str

    def to_dict(self):
        return {"type": "TagIdFilter", "tagId": self.tag_id}


@dataclass
class SearchFilter:
    """
    Search filters are composites of match any or match all clauses
    param: matchAll -> true or false
    """

    match_all_filters: List[MatchFilter] = field(default_factory=list)
    match_any_filters: List[MatchFilter] = field(default_factory=list)

    def to_dict(self):
        return {
            "searchFilters": [
                {
                    "matchAll": True,
                    "filters": [
                        match_filter.to_dict()
                        for match_filter in self.match_all_filters
                    ],
                },
                {
                    "matchAll": False,
                    "filters": [
                        match_filter.to_dict()
                        for match_filter in self.match_any_filters
                    ],
                },
            ]
        }


@dataclass
class TrendRequest:
    """
    Helper class to construct a trend request payload

    Parameters
    ----------
    object : _type_
        _description_
    """

    report_view: ReportView
    date_filter: DateFilter
    search_filters: SearchFilter
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

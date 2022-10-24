"""
General Filters helper classes
"""

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Union


@dataclass
class MatchFilter(metaclass=ABCMeta):
    @abstractmethod
    def to_dict(self):
        pass


@dataclass
class AccountIdFilter(MatchFilter):
    value: str

    def to_dict(self):
        return {"type": "AccountIdFilter", "accountId": self.value}


@dataclass
class CategoryIdFilter(MatchFilter):
    value: str
    include_child_categories: bool

    def to_dict(self):
        return {
            "type": "CategoryIdFilter",
            "categoryId": self.value,
            "includeChildCategories": self.include_child_categories,
        }


@dataclass
class CategoryNameFilter(MatchFilter):
    value: str
    include_child_categories: bool

    def to_dict(self):
        return {
            "type": "CategoryNameFilter",
            "categoryName": self.value,
            "includeChildCategories": self.include_child_categories,
            "exclude": True,
        }


@dataclass
class DescriptionNameFilter(MatchFilter):
    value: str

    def to_dict(self):
        return {"type": "DescriptionNameFilter", "description": self.value}


@dataclass
class TagIdFilter(MatchFilter):
    value: str

    def to_dict(self):
        return {"type": "TagIdFilter", "tagId": self.value}


@dataclass
class TagNameFilter(MatchFilter):
    value: str

    def to_dict(self):
        return {"type": "TagNameFilter", "tagName": self.value, "exclude": True}


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
            assert self.start_date is not None or self.end_date is not None

    def to_dict(self):
        filter_clause = {"dateFilter": {"type": self.date_filter}}
        if self.date_filter == self.Options.CUSTOM.name:
            filter_clause["dateFilter"]["startDate"] = self.start_date
            filter_clause["dateFilter"]["endDate"] = self.end_date
        return filter_clause


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

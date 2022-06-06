"""
General Filters helper classes
"""

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import List


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

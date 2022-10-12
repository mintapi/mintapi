"""
Transactions helper classes
"""

from dataclasses import dataclass
from mintapi.filters import SearchFilter, DateFilter


@dataclass
class TransactionRequest:
    """
    Helper class to construct a transaction request payload

    Parameters
    ----------
    object : _type_
        _description_
    """

    date_filter: DateFilter
    search_filters: SearchFilter
    # NOTE: This is included even though it is not used so that we can keep a
    #       general method in api.py for creating requests.
    report_view: str = None
    limit: int = 5000
    offset: int = 0

    def to_dict(self):
        return {
            **self.date_filter.to_dict(),
            **self.search_filters.to_dict(),
            "limit": self.limit,
            "offset": self.offset,
        }

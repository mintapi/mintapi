"""
Transactions helper classes
"""

from dataclasses import dataclass
from enum import Enum
from typing import List

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


@dataclass
class TransactionUpdateRequest:
    class TransactionType(Enum):
        CashAndCreditTransaction = "CashAndCreditTransaction"
        InvestmentTransaction = "InvestmentTransaction"
        LoanTransaction = "LoanTransaction"

    """
    Helper class to construct a transaction update request payload.

    Parameters
    ----------
    type : TransactionType
        The type of transaction to update.
    description : str, optional
        Optional description to assign to the transaction.
    notes : str, optional
        Optional notes to associate with the transaction.
    category_id : str, optional
        Optional category ID to assign to the transaction.
    tag_ids : List[str], optional
        Optional list of tag IDs to assign to the transaction.

    Raises
    ------
    ValueError
        If the transaction type is not one of the allowed values in the `TransactionUpdateRequest.TransactionType` enum.
    """
    type: TransactionType
    description: str = None
    notes: str = None
    category_id: str = None
    tag_ids: List[str] = None

    def __post_init__(self):
        if isinstance(self.type, str):
            assert hasattr(self.TransactionType, self.type)
        else:
            raise ValueError(
                "Transaction Type must be one of allowed values in enum `TransactionUpdateRequest.TransactionType"
            )

    def to_dict(self):
        payload = {
            "type": self.type,
        }
        if self.description is not None:
            payload["description"] = self.description
        if self.notes is not None:
            payload["notes"] = self.notes
        if self.category_id is not None:
            payload["category"] = {
                "id": self.category_id,
            }
        if self.tag_ids is not None:
            payload["tagData"] = {
                "tags": [{"id": tag_id} for tag_id in self.tag_ids],
            }
        return payload

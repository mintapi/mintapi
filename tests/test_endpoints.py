"""
Data extraction endpoint tests

Mocks api with fixed responses and validates requests are correctly structured
"""
import unittest
from unittest.mock import patch

import pytest
from mintapi.endpoints import MintEndpoints


class PaginationTests(unittest.TestCase):
    pass


class EndpointRequestTests(unittest.TestCase):
    """
    Verifies correct urls + params passed and
    parsing of mock responses returned
    """


class UserMethodEndpointTests(unittest.TestCase):
    """
    Focuses on postprocessing of raw json results (assumes api response verified separately)
    """


if __name__ == "__main__":
    pytest.main()

"""
Data extraction endpoint tests

Mocks api with fixed responses and validates requests are correctly structured
"""
import sys
import unittest
from unittest.mock import patch

import mintapi.endpoints
import pytest
from mintapi.endpoints import MintEndpoints


class PaginationTests(unittest.TestCase):
    class FakeNextResponse(object):
        def json(self):
            return {
                "Transaction": [
                    {"id": 0, "other": "value"},
                    {"id": 1, "other": "value2"},
                ],
                "metaData": {
                    "asOf": "2022-12-05T00:15:08Z",
                    "totalSize": 2,
                    "pageSize": 1,
                    "currentPage": 1,
                    "offset": 0,
                    "limit": 1,
                    "link": [
                        {
                            "otherAttributes": {"method": "GET"},
                            "href": "/v1/transactions/search",
                            "rel": "self",
                        },
                        {
                            "otherAttributes": {},
                            "href": "/v1/transactions/search?offset=0&limit=1",
                            "rel": "prev",
                        },
                        {
                            "otherAttributes": {},
                            "href": "/v1/transactions/search?offset=1&limit=1",
                            "rel": "next",
                        },
                    ],
                    "sortBy": "DATE_DESCENDING",
                },
            }

    class FakeResponse(object):
        def json(self):
            return {
                "Transaction": [
                    {"id": 3, "other": "value3"},
                    {"id": 4, "other": "value4"},
                ],
                "metaData": {
                    "asOf": "2022-12-05T00:15:08Z",
                    "totalSize": 2,
                    "pageSize": 1,
                    "currentPage": 2,
                    "offset": 1,
                    "limit": 1,
                    "link": [
                        {
                            "otherAttributes": {"method": "GET"},
                            "href": "/v1/transactions/search?offset=1&limit=1",
                            "rel": "self",
                        },
                        {
                            "otherAttributes": {},
                            "href": "/v1/transactions/search?offset=0&limit=1",
                            "rel": "prev",
                        },
                    ],
                    "sortBy": "DATE_DESCENDING",
                },
            }

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    def test_missing_data_key(self, _):
        """
        Returns empty list
        """
        endpoints = MintEndpoints()
        data = endpoints._paginate(
            data_key="non_existent_key",
            metadata_key="metaData",
            response=self.FakeNextResponse(),
        )

        self.assertEqual(
            data,
            [],
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    def test_missing_metadata_key(self, _):
        """
        Returns initial data only
        """
        endpoints = MintEndpoints()
        data = endpoints._paginate(
            data_key="Transaction",
            metadata_key="non_existent_key",
            response=self.FakeNextResponse(),
        )

        self.assertEqual(
            data,
            [
                {"id": 0, "other": "value"},
                {"id": 1, "other": "value2"},
            ],
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_metadata_next_handling(self, mock_request, _):
        """
        Should recurse
        """
        mock_request.return_value = self.FakeResponse()
        endpoints = MintEndpoints()
        data = endpoints._paginate(
            data_key="Transaction",
            metadata_key="metaData",
            response=self.FakeNextResponse(),
        )

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key="Transaction",
            metadata_key="metaData",
            paginate=False,
            uri_path="/v1/transactions/search?offset=1&limit=1",
        )

        # assert data extracted
        self.assertEqual(
            data,
            [
                {"id": 0, "other": "value"},
                {"id": 1, "other": "value2"},
                {"id": 3, "other": "value3"},
                {"id": 4, "other": "value4"},
            ],
        )


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
    pytest.main(sys.argv)

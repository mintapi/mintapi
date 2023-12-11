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
            method="POST",
        )

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key="Transaction",
            metadata_key="metaData",
            paginate=False,
            uri_path="/v1/transactions/search?offset=1&limit=1",
            method="POST",
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

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_account_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        data = endpoints._get_account_data()
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key="Account",
            metadata_key="metaData",
            api_section="/pfm",
            api_url="https://mint.intuit.com",
            method="GET",
            uri_path="/v1/accounts",
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_budget_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        data = endpoints._get_budget_data()
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key="Budget",
            metadata_key="metaData",
            api_section="/pfm",
            api_url="https://mint.intuit.com",
            method="GET",
            uri_path="/v1/budgets",
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_bills_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        data = endpoints._get_bills_data()
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key="bills",
            metadata_key="collectionMetaData",
            api_section="/bps",
            api_url="https://mint.intuit.com",
            method="GET",
            uri_path="/v2/payer/bills",
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_category_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        data = endpoints._get_category_data()
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key="Category",
            metadata_key="metaData",
            api_section="/pfm",
            api_url="https://mint.intuit.com",
            method="GET",
            uri_path="/v1/categories",
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_tag_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        data = endpoints._get_tag_data()
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key="Tag",
            metadata_key="metaData",
            api_section="/pfm",
            api_url="https://mint.intuit.com",
            method="GET",
            uri_path="/v1/tags",
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_rule_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        data = endpoints._get_rules_data()
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key="TransactionRules",
            metadata_key="metaData",
            api_section="/pfm",
            api_url="https://mint.intuit.com",
            method="GET",
            uri_path="/v1/transaction-rules",
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_credit_account_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        data = endpoints._get_credit_accounts()
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key=None,
            metadata_key=None,
            api_section="",
            api_url="https://credit.finance.intuit.com",
            method="GET",
            uri_path="/v1/creditreports/0/tradelines",
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_credit_inquiries_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        data = endpoints._get_credit_inquiries()
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key=None,
            metadata_key=None,
            api_section="",
            api_url="https://credit.finance.intuit.com",
            method="GET",
            uri_path="/v1/creditreports/0/inquiries",
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_credit_reports_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        data = endpoints._get_credit_reports()
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key=None,
            metadata_key=None,
            api_section="",
            api_url="https://credit.finance.intuit.com",
            method="GET",
            uri_path="/v1/creditreports",
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_credit_utilization_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        data = endpoints._get_credit_utilization()
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key=None,
            metadata_key=None,
            api_section="",
            api_url="https://credit.finance.intuit.com",
            method="GET",
            uri_path="/v1/creditreports/creditutilizationhistory",
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_investment_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        data = endpoints._get_investment_data()
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key="Investment",
            metadata_key="metaData",
            api_section="/pfm",
            api_url="https://mint.intuit.com",
            method="GET",
            uri_path="/v1/investments",
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_transaction_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        data = endpoints._get_transaction_data()
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key="Transaction",
            metadata_key="metaData",
            api_section="/pfm",
            api_url="https://mint.intuit.com",
            method="POST",
            uri_path="/v1/transactions/search",
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_trend_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        data = endpoints._get_trend_data()
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key="Trend",
            metadata_key="metaData",
            api_section="/pfm",
            api_url="https://mint.intuit.com",
            method="POST",
            uri_path="/v1/trends",
        )

    @patch.object(
        mintapi.endpoints.MintEndpoints, "__abstractmethods__", new_callable=set
    )
    @patch.object(mintapi.endpoints.MintEndpoints, "request")
    def test_update_transaction_endpoint(self, mock_request, _):
        """
        Tests params are correctly passed to the request method
        """
        # Future TODO: mock full api response
        mock_request.return_value = None
        endpoints = MintEndpoints()
        transaction_id = "1"
        data = endpoints._update_transaction(
            transaction_id="1",
        )
        self.assertIsNone(data)

        # assert pagination call
        mock_request.assert_called_once_with(
            data_key=None,
            metadata_key=None,
            api_section="/pfm",
            api_url="https://mint.intuit.com",
            method="PUT",
            uri_path=f"/v1/transactions/{transaction_id}",
        )


class UserMethodEndpointTests(unittest.TestCase):
    """
    Focuses on postprocessing of raw json results (assumes api response verified separately)
    """


if __name__ == "__main__":
    pytest.main(sys.argv)

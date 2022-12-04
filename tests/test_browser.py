import unittest
from unittest.mock import patch

import mintapi.browser
from mintapi.browser import SeleniumBrowser


class BrowserSignInTests(unittest.TestCase):
    @patch.object(mintapi.browser, "_create_web_driver_at_mint_com")
    @patch.object(mintapi.browser, "logger")
    @patch.object(mintapi.browser, "sign_in")
    def test_when_sign_in_fails_then_logs_exception(
        self, mock_sign_in, mock_logger, *_
    ):
        test_exception = Exception()
        mock_sign_in.side_effect = test_exception
        with self.assertRaises(Exception) as context:
            SeleniumBrowser("test", "test")
        mock_logger.exception.assert_called_with(test_exception)
        self.assertTrue("Could not sign in to Mint" in str(context.exception))


class BrowserAuthTests(unittest.TestCase):
    # Future TODO: these would be more exciting as an integration test with
    # a real selenium driver
    def test_extracting_api_key_header(self):
        pass

    def test_getting_cookies(self):
        pass


class BrowserRequestHandlingTests(unittest.TestCase):
    def test_header_injection(self):
        pass

    def test_request_param_passing(self):
        pass

    def test_response_status_checking(self):
        pass

    def test_pagination_call(self):
        pass


class BrowserEndpointTests(unittest.TestCase):
    """
    E2E browser endpoint test with mock endpoint responses
    (endpoint logic tested separately)
    """

    # @patch.multiple(
    #     SeleniumBrowser,
    #     _get_api_key_header=DEFAULT,
    #     _load_mint_credit_url=DEFAULT,
    #     _get_credit_reports=DEFAULT,
    #     get_credit_accounts=DEFAULT,
    #     get_credit_inquiries=DEFAULT,
    #     get_credit_utilization=DEFAULT,
    # )
    # def test_exclude_credit_details(self, **_):
    #     mint = SeleniumBrowser()
    #     credit_report = mint.get_credit_report_data(
    #         limit=2, details=True, exclude_inquiries=True
    #     )
    #     self.assertFalse("inquiries" in credit_report)
    #     credit_report = mint.get_credit_report_data(
    #         limit=2, details=True, exclude_inquiries=False
    #     )
    #     self.assertTrue("inquiries" in credit_report)
    #     credit_report = mint.get_credit_report_data(
    #         limit=2, details=True, exclude_accounts=True
    #     )
    #     self.assertFalse("accounts" in credit_report)
    #     credit_report = mint.get_credit_report_data(
    #         limit=2, details=True, exclude_accounts=False
    #     )
    #     self.assertTrue("accounts" in credit_report)
    #     credit_report = mint.get_credit_report_data(
    #         limit=2, details=True, exclude_utilization=True
    #     )
    #     self.assertFalse("utilization" in credit_report)
    #     credit_report = mint.get_credit_report_data(
    #         limit=2, details=True, exclude_utilization=False
    #     )
    #     self.assertTrue("utilization" in credit_report)

    # @patch.object(SeleniumBrowser, "_Mint__get_mint_endpoint")
    # def test_get_account_data(self, mock_call_accounts_endpoint):
    #     mock_call_accounts_endpoint.return_value = accounts_example
    #     account_data = SeleniumBrowser().get_account_data()[0]
    #     self.assertFalse("metaData" in account_data)
    #     self.assertTrue("createdDate" in account_data)
    #     self.assertTrue("lastUpdatedDate" in account_data)

    # @patch.object(SeleniumBrowser, "_Mint__post_mint_endpoint")
    # def test_get_transaction_data(self, mock_call_transactions_endpoint):
    #     mock_call_transactions_endpoint.return_value = transactions_example
    #     transaction_data = SeleniumBrowser().get_transaction_data()[0]
    #     self.assertFalse("metaData" in transaction_data)
    #     self.assertFalse("createdDate" in transaction_data)
    #     self.assertTrue("lastUpdatedDate" in transaction_data)
    #     self.assertTrue("parentId" in transaction_data["category"])
    #     self.assertTrue("parentName" in transaction_data["category"])

    # @patch.object(SeleniumBrowser, "_Mint__get_mint_endpoint")
    # def test_get_investment_data(self, mock_call_investments_endpoint):
    #     mock_call_investments_endpoint.return_value = investments_example
    #     investment_data = SeleniumBrowser().get_investment_data()[0]
    #     self.assertFalse("metaData" in investment_data)
    #     self.assertFalse("createdDate" in investment_data)
    #     self.assertTrue("lastUpdatedDate" in investment_data)

    # @patch.object(SeleniumBrowser, "_Mint__get_mint_endpoint")
    # def test_get_budgets(self, mock_call_budgets_endpoint):
    #     mock_call_budgets_endpoint.return_value = budgets_example
    #     budgets = SeleniumBrowser().get_budget_data()[0]
    #     self.assertFalse("metaData" in budgets)
    #     self.assertTrue("createdDate" in budgets)
    #     self.assertTrue("lastUpdatedDate" in budgets)


if __name__ == "__main__":
    unittest.main()

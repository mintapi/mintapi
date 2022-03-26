import mintapi.api
import mintapi.cli
import mintapi.signIn
import copy
import datetime
import json
import unittest

import pandas as pd

import requests
import tempfile

from unittest.mock import patch, DEFAULT


accounts_example = [
    {
        "accountName": "Chase Checking",
        "lastUpdated": 1401201492000,
        "lastUpdatedInString": "25 minutes",
        "accountType": "bank",
        "currentBalance": 100.12,
    }
]

category_example = [
    {
        "type": "Category",
        "name": "Entertainment",
        "depth": 1,
        "categoryType": "EXPENSE",
        "isBusiness": "false",
        "isCustom": "false",
        "isUnassignable": "false",
        "isUnbudgetable": "false",
        "isUntrendable": "false",
        "isIgnored": "false",
        "isEditable": "false",
        "isDeleted": "false",
        "discretionaryType": "DISCRETIONARY",
        "metaData": {
            "lastUpdatedDate": "2020-11-18T07:31:47Z",
            "link": [
                {
                    "otherAttributes": {},
                    "href": "/v1/categories/10740790_1",
                    "rel": "self",
                }
            ],
        },
        "id": "10740790_14",
    },
    {
        "type": "Category",
        "name": "Auto Insurance",
        "depth": 2,
        "categoryType": "EXPENSE",
        "parentId": "10740790_14",
        "isBusiness": False,
        "isCustom": False,
        "isUnassignable": False,
        "isUnbudgetable": False,
        "isUntrendable": False,
        "isIgnored": False,
        "isEditable": False,
        "isDeleted": False,
        "discretionaryType": "NON_DISCRETIONARY",
        "metaData": {
            "lastUpdatedDate": "2020-11-18T07:31:47Z",
            "link": [
                {
                    "otherAttributes": {},
                    "href": "/v1/categories/10740790_1405",
                    "rel": "self",
                }
            ],
        },
        "id": "10740790_1405",
    },
]

detailed_transactions_example = {
  "Transaction": [
    {
      "type": "CashAndCreditTransaction",
      "metaData": {
        "lastUpdatedDate": "2022-03-25T00:11:08Z",
        "link": [
          {
            "otherAttributes": {},
            "href": "/v1/transactions/id",
            "rel": "self"
          }
        ]
      },
      "id": "id",
      "accountId": "accountId",
      "accountRef": {
        "id": "id",
        "name": "name",
        "type": "BankAccount",
        "hiddenFromPlanningAndTrends": "false"
      },
      "date": "2022-03-24",
      "description": "description",
      "category": {
        "id": "id",
        "name": "Income",
        "categoryType": "INCOME",
        "parentId": "parentId",
        "parentName": "Root"
      },
      "amount": 420.0,
      "status": "MANUAL",
      "matchState": "NOT_MATCHED",
      "fiData": {
        "id": "id",
        "date": "2022-03-24",
        "amount": 420.0,
        "description": "description",
        "inferredDescription": "inferredDescription",
        "inferredCategory": {
          "id": "id",
          "name": "name"
        }
      },
      "etag": "etag",
      "isExpense": "false",
      "isPending": "true",
      "discretionaryType": "NONE",
      "isLinkedToRule": "false",
      "transactionReviewState": "NOT_APPLICABLE"
    },
  ]
}

investments_example = {
    "Investment": [
        {
            "accountId": "1",
            "cpSrcElementId": "2",
            "description": "TEST",
            "cpAssetClass": "UNKNOWN",
            "holdingType": "UNKNOWN",
            "initialTotalCost": 0.0,
            "inceptionDate": "2011-01-03T07:00:00Z",
            "initialQuantity": 0.0,
            "currentQuantity": 0.0,
            "currentPrice": 10.0,
            "currentValue": 1414.12,
            "averagePricePaid": 0.0,
            "id": "3",
            "metaData": {
                "lastUpdatedDate": "2011-11-03T07:00:00Z",
                "link": [{"id": "4", "description": "METADATA TEST"}],
            },
        }
    ]
}

budgets_example = {
    "Budget": [
        {
            "type": "MonthlyBudget",
            "budgetAdjustmentAmount": -75.00,
            "rollover": "true",
            "reset": "false",
            "rolloverResetAmount": 0.0,
            "metaData": {
                "createdDate": "2022-03-01T08:00:00Z",
                "lastUpdatedDate": "2022-02-28T08:32:50Z",
                "link": [
                    {
                        "otherAttributes": {},
                        "href": "/v1/budgets/10740790_2123123684",
                        "rel": "self",
                    }
                ],
            },
            "id": "10740790_2123123684",
            "budgetDate": "2022-03-01",
            "amount": 75.00,
            "budgetAmount": 50.0,
            "category": {
                "id": "10740790_11235",
                "name": "Auto Insurance",
                "categoryType": "EXPENSE",
                "parentId": "14",
                "parentName": "Auto & Transport",
            },
            "subsumed": "false",
            "performanceStatus": "OVERBUDGET",
        },
    ]
}


class Attribute:
    text = json.dumps({"response": {"42": {"response": accounts_example}}})


class Element:
    @staticmethod
    def get_attribute(test):
        return json.dumps({"token": "123"})


class TestMock:
    @staticmethod
    def find_element_by_name(test):
        return Element()

    @staticmethod
    def request(a, b, **c):
        return Attribute()


class MintApiTests(unittest.TestCase):
    @patch.object(mintapi.api, "sign_in")
    @patch.object(mintapi.api, "_create_web_driver_at_mint_com")
    def test_accounts(self, mock_driver, mock_sign_in):
        mock_driver.return_value = TestMock()
        mock_sign_in.return_value = ("test", "token")
        accounts = mintapi.get_accounts("foo", "bar")

        self.assertFalse("lastUpdatedInDate" in accounts)
        self.assertNotEqual(accounts, accounts_example)

        accounts_annotated = copy.deepcopy(accounts_example)
        for account in accounts_annotated:
            account["lastUpdatedInDate"] = datetime.datetime.fromtimestamp(
                account["lastUpdated"] / 1000
            )
        self.assertEqual(accounts, accounts_annotated)

        # ensure everything is json serializable as this is the command-line
        # behavior.
        mintapi.cli.print_accounts(accounts)

    def test_chrome_driver_links(self):
        latest_version = mintapi.signIn.get_latest_chrome_driver_version()
        for platform in mintapi.signIn.CHROME_ZIP_TYPES:
            request = requests.get(
                mintapi.signIn.get_chrome_driver_url(latest_version, platform)
            )
            self.assertEqual(request.status_code, 200)

    def test_parse_float(self):

        answer = mintapi.api.parse_float("10%")
        self.assertEqual(answer, float(10))

        answer = mintapi.api.parse_float("$10")
        self.assertEqual(answer, float(10))

        answer = mintapi.api.parse_float("0.00%")
        self.assertEqual(answer, float(0))

    @patch.object(mintapi.Mint, "get_categories")
    def test_detailed_transactions_with_parents(self, mock_get_categories):
        mock_get_categories.return_value = category_example
        results_with_parents = mintapi.Mint().add_parent_category_to_result(
            detailed_transactions_example
        )[0]
        self.assertTrue("parentCategoryName" in results_with_parents)
        self.assertTrue("parentCategoryId" in results_with_parents)

    @patch.object(mintapi.api, "_create_web_driver_at_mint_com")
    @patch.object(mintapi.api, "logger")
    @patch.object(mintapi.api, "sign_in")
    def test_when_sign_in_fails_then_logs_exception(
        self, mock_sign_in, mock_logger, *_
    ):
        test_exception = Exception()
        mock_sign_in.side_effect = test_exception
        mintapi.Mint("test", "test")
        mock_logger.exception.assert_called_with(test_exception)

    @patch.multiple(
        mintapi.Mint,
        _get_api_key_header=DEFAULT,
        _load_mint_credit_url=DEFAULT,
        _get_credit_reports=DEFAULT,
        get_credit_accounts=DEFAULT,
        get_credit_inquiries=DEFAULT,
        get_credit_utilization=DEFAULT,
    )
    def test_exclude_credit_details(self, **_):
        mint = mintapi.Mint()
        credit_report = mint.get_credit_report(
            limit=2, details=True, exclude_inquiries=True
        )
        self.assertFalse("inquiries" in credit_report)
        credit_report = mint.get_credit_report(
            limit=2, details=True, exclude_inquiries=False
        )
        self.assertTrue("inquiries" in credit_report)
        credit_report = mint.get_credit_report(
            limit=2, details=True, exclude_accounts=True
        )
        self.assertFalse("accounts" in credit_report)
        credit_report = mint.get_credit_report(
            limit=2, details=True, exclude_accounts=False
        )
        self.assertTrue("accounts" in credit_report)
        credit_report = mint.get_credit_report(
            limit=2, details=True, exclude_utilization=True
        )
        self.assertFalse("utilization" in credit_report)
        credit_report = mint.get_credit_report(
            limit=2, details=True, exclude_utilization=False
        )
        self.assertTrue("utilization" in credit_report)

    def test_config_file(self):
        # verify parsing from config file
        config_file = write_extended_transactions_file()
        arguments = parse_arguments_file(config_file)
        self.assertEqual(arguments.extended_transactions, True)
        config_file.close()

    @patch.object(mintapi.signIn, "get_web_driver")
    def test_build_bundledServiceController_url(self, mock_driver):
        mock_driver.return_value = (TestMock(), "test")
        url = mintapi.Mint.build_bundledServiceController_url(mock_driver)
        self.assertTrue(mintapi.api.MINT_ROOT_URL in url)

    @patch.object(mintapi.Mint, "_Mint__call_investments_endpoint")
    def test_get_investment_data_new(self, mock_call_investments_endpoint):
        mock_call_investments_endpoint.return_value = investments_example
        investment_data = mintapi.Mint().get_investment_data()[0]
        self.assertFalse("metaData" in investment_data)
        self.assertTrue("lastUpdatedDate" in investment_data)

    @patch.object(mintapi.Mint, "_Mint__call_budgets_endpoint")
    def test_get_budgets(self, mock_call_budgets_endpoint):
        mock_call_budgets_endpoint.return_value = budgets_example
        budgets = mintapi.Mint().get_budgets()[0]
        self.assertFalse("metaData" in budgets)
        self.assertTrue("lastUpdatedDate" in budgets)

    def test_validate_file_extensions(self):
        config_file = write_extended_transactions_file()
        config_file.write("filename=/tmp/transactions.txt")
        arguments = parse_arguments_file(config_file)
        self.assertRaises(ValueError, mintapi.cli.validate_file_extensions, arguments)
        config_file = write_extended_transactions_file()
        config_file.write("filename=/tmp/transactions.csv")
        arguments = parse_arguments_file(config_file)
        self.assertEqual(mintapi.cli.validate_file_extensions(arguments), None)
        config_file = write_accounts_file()
        config_file.write("filename=/tmp/accounts.csv")
        arguments = parse_arguments_file(config_file)
        self.assertRaises(ValueError, mintapi.cli.validate_file_extensions, arguments)
        config_file = write_accounts_file()
        config_file.write("filename=/tmp/accounts.json")
        arguments = parse_arguments_file(config_file)
        self.assertEqual(mintapi.cli.validate_file_extensions(arguments), None)

    def test_include_investments_with_transactions(self):
        mint = mintapi.Mint()
        self.assertFalse(mint._include_investments_with_transactions(0, False))
        self.assertTrue(mint._include_investments_with_transactions(0, True))
        self.assertTrue(mint._include_investments_with_transactions(1, False))
        self.assertTrue(mint._include_investments_with_transactions(1, True))


def write_extended_transactions_file():
    config_file = tempfile.NamedTemporaryFile(mode="wt")
    config_file.write("extended-transactions\n")
    return config_file


def write_accounts_file():
    config_file = tempfile.NamedTemporaryFile(mode="wt")
    config_file.write("accounts\n")
    return config_file


def parse_arguments_file(config_file):
    config_file.flush()
    return mintapi.cli.parse_arguments(["-c", config_file.name])


if __name__ == "__main__":
    unittest.main()

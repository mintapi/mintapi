import mintapi.api
import mintapi
import copy
import datetime
import json
import unittest
import os

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

category_example = {
    708: {
        "categoryType": "EXPENSE",
        "parent": {
            "categoryType": "EXPENSE",
            "parent": {
                "categoryType": "NO_CATEGORY",
                "parent": None,
                "depth": 0,
                "name": "Root",
                "id": 0,
                "notificationName": "Everything Else",
                "parentId": 0,
                "precedence": 100,
            },
            "depth": 1,
            "name": "Food & Dining",
            "id": 7,
            "notificationName": "Food & Dining",
            "parentId": 0,
            "precedence": 30,
        },
        "depth": 2,
        "name": "Alcohol & Bars",
        "id": 708,
        "notificationName": "Alcohol & Bars",
        "parentId": 7,
        "precedence": 20,
    }
}

detailed_transactions_example = [
    {
        "date": "Oct 22",
        "note": "",
        "isPercent": False,
        "fi": "",
        "txnType": 0,
        "numberMatchedByRule": -1,
        "isEdited": False,
        "isPending": False,
        "mcategory": "Alcohol & Bars",
        "isMatched": False,
        "odate": "2021-10-22",
        "isFirstDate": True,
        "id": 1,
        "isDuplicate": False,
        "hasAttachments": False,
        "isChild": False,
        "isSpending": True,
        "amount": 17.16,
        "ruleCategory": "",
        "userCategoryId": "",
        "isTransfer": False,
        "isAfterFiCreationTime": True,
        "merchant": "TRIMTAB BREWING COMPANY",
        "manualType": 0,
        "labels": [],
        "mmerchant": "TRIMTAB BREWING COMPANY",
        "isCheck": False,
        "omerchant": "TRIMTAB BREWING COMPANY",
        "isDebit": True,
        "category": "Alcohol & Bars",
        "ruleMerchant": "",
        "isLinkedToRule": False,
        "account": "CREDIT CARD",
        "categoryId": 708,
        "ruleCategoryId": 0,
    }
]

transactions_example = b'"Date","Description","Original Description","Amount","Transaction Type","Category","Account Name","Labels","Notes"\n"5/14/2020","Safeway","SAFEWAY.COM # 3031","88.09","debit","Groceries","CREDIT CARD","",""\n'

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
        mintapi.print_accounts(accounts)

    def test_chrome_driver_links(self):
        latest_version = mintapi.api.get_latest_chrome_driver_version()
        for platform in mintapi.api.CHROME_ZIP_TYPES:
            request = requests.get(
                mintapi.api.get_chrome_driver_url(latest_version, platform)
            )
            self.assertEqual(request.status_code, 200)

    def test_parse_float(self):

        answer = mintapi.api.parse_float("10%")
        self.assertEqual(answer, float(10))

        answer = mintapi.api.parse_float("$10")
        self.assertEqual(answer, float(10))

        answer = mintapi.api.parse_float("0.00%")
        self.assertEqual(answer, float(0))

    @patch.object(mintapi.Mint, "get_transactions_csv")
    def test_get_transactions(self, mocked_get_transactions):
        mocked_get_transactions.return_value = transactions_example
        mint = mintapi.Mint()
        transactions_df = mint.get_transactions()
        assert isinstance(transactions_df, pd.DataFrame)

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
        config_file = tempfile.NamedTemporaryFile(mode="wt")
        config_file.write("extended-transactions")
        config_file.flush()
        arguments = mintapi.api.parse_arguments(["-c", config_file.name])
        self.assertEqual(arguments.extended_transactions, True)
        config_file.close()

    @patch.object(mintapi.api, "get_web_driver")
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


if __name__ == "__main__":
    unittest.main()

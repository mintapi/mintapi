accounts_example = {
    "Account": [
        {
            "type": "CreditAccount",
            "userCardType": "UNKNOWN",
            "creditAccountType": "CREDIT_CARD",
            "creditLimit": 2222.0,
            "availableCredit": 1111.0,
            "interestRate": 0.444,
            "minPayment": 111.0,
            "absoluteMinPayment": 111.0,
            "statementMinPayment": 22.0,
            "statementDueDate": "2022-04-19T07:00:00Z",
            "statementDueAmount": 0.0,
            "metaData": {
                "createdDate": "2017-01-05T17:12:15Z",
                "lastUpdatedDate": "2022-03-27T16:46:41Z",
                "link": [
                    {
                        "otherAttributes": {},
                        "href": "/v1/accounts/id",
                        "rel": "self",
                    }
                ],
            },
            "id": "id",
            "name": "name",
            "value": -555.55,
            "isVisible": True,
            "isDeleted": False,
            "planningTrendsVisible": True,
            "accountStatus": "ACTIVE",
            "systemStatus": "ACTIVE",
            "currency": "USD",
            "fiLoginId": "fiLoginId",
            "fiLoginStatus": "OK",
            "currentBalance": 555.55,
            "cpId": "cpId",
            "cpAccountName": "cpAccountName",
            "cpAccountNumberLast4": "cpAccountNumberLast4",
            "hostAccount": False,
            "fiName": "fiName",
            "accountTypeInt": 0,
            "isAccountClosedByMint": False,
            "isAccountNotFound": False,
            "isActive": True,
            "isClosed": False,
            "isError": False,
            "isHiddenFromPlanningTrends": True,
            "isTerminal": True,
            "credentialSetId": "credentialSetId",
            "ccAggrStatus": "0",
        }
    ]
}


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

transactions_example = {
    "Transaction": [
        {
            "type": "CashAndCreditTransaction",
            "metaData": {
                "lastUpdatedDate": "2022-03-25T00:11:08Z",
                "link": [
                    {
                        "otherAttributes": {},
                        "href": "/v1/transactions/id",
                        "rel": "self",
                    }
                ],
            },
            "id": "id",
            "accountId": "accountId",
            "accountRef": {
                "id": "id",
                "name": "name",
                "type": "BankAccount",
                "hiddenFromPlanningAndTrends": False,
            },
            "date": "2022-03-24",
            "description": "description",
            "category": {
                "id": "id",
                "name": "Income",
                "categoryType": "INCOME",
                "parentId": "parentId",
                "parentName": "Root",
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
                "inferredCategory": {"id": "id", "name": "name"},
            },
            "etag": "etag",
            "isExpense": False,
            "isPending": False,
            "discretionaryType": "NONE",
            "isLinkedToRule": False,
            "transactionReviewState": "NOT_APPLICABLE",
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

mintapi
=======

a screen-scraping API for Mint.com.

Requirements
===
Ensure you have Python 2 or 3 and pip (`easy_install pip`) and then:

    pip install mintapi

Usage
===

from Python
---
From python, simply call `get_accounts`. We recommend using the
`keyring` library for persisting credentials.

    import mintapi
    accounts = mintapi.get_accounts(email, password)

from anywhere
---
Run it as a sub-process from your favorite language. From the command-line, the output is JSON:

    >>> mintapi email password
    [
      {
        "accountName": "Chase Checking", 
        "lastUpdatedInString": "25 minutes", 
        "accountType": "bank", 
        "currentBalance": 100.12,
        ...
      },
      ...
    ]

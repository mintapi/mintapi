mintapi
=======

a screen-scraping API for Mint.com

Requirements
===
pip install pyquery

Usage
===

from Python
---
    import mint
    accounts = mint.get_accounts(email, password)

from anywhere
---
From the command-line, the output is JSON:
    >>> python mint.py email password
    [
      {
        "accountName": "Chase Checking", 
        "lastUpdatedInString": "25 minutes", 
        "accountType": "bank", 
        "currentBalance": 100.12,
        ...
      }
      ...
    ]

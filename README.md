mintapi
=======

a screen-scraping API for Mint.com. [![Build Status](https://travis-ci.org/mrooney/mintapi.svg?branch=master)](https://travis-ci.org/mrooney/mintapi)

Requirements
===
Ensure you have Python 2 or 3 and pip (`easy_install pip`) and then:

    pip install mintapi

Usage
===

from Python
---
From python, instantiate the Mint class (from the mintapi package) and you can
make calls to retrieve account/budget information.  We recommend using the
`keyring` library for persisting credentials.

    import mintapi
    mint = mintapi.Mint(email, password)
    
    # Get basic account information
    mint.get_accounts()
    
    # Get extended account detail at the expense of speed - requires an
    # additional API call for each account
    mint.get_accounts(True)
    
    # Get budget information
    mint.get_budgets()
    
    # Initiate an account refresh
    mint.initiate_account_refresh()

    # Get all transactions (could take a while)
    mint.get_transactions()


from anywhere
---
Run it as a sub-process from your favorite language; `pip install mintapi` creates a binary in your $PATH. From the command-line, the output is JSON:

    Usage: api.py [options] email password

    Options:
      -h, --help           show this help message and exit
      --accounts           Retrieve account information (default if nothing else is specified)
      --budgets            Retrieve budget information
      --extended-accounts  Retrieve extended account information (slower, implies --accounts)
      
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



If you need to avoid using pip or setup.py, you can also clone/download
this repository and run: `python mintapi/main.py email password`

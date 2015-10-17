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

    # Get transactions
    mint.get_transactions() # as pandas dataframe
    mint.get_transactions_csv(self, include_investment=False) # as raw csv data
    mint.get_transactions_json(self, include_investment=False, skip_duplicates=False):

    # Get net worth
    mint.get_net_worth()

    # Initiate an account refresh
    mint.initiate_account_refresh()

There are, additionally, deprecated wrappers for backward compatibility with
old versions of the API.

    import mintapi
    mintapi.get_accounts(email, password)
    mintapi.get_accounts(email, password, True)
    mintapi.get_budgets(email, password)
    mintapi.initiate_account_refresh(email, password)

from anywhere
---
Run it as a sub-process from your favorite language; `pip install mintapi` creates a binary in your $PATH. From the command-line, the output is JSON:

    usage: mintapi [-h] [--accounts] [--budgets] [--extended-accounts]
                   [--transactions] [--filename FILENAME] [--keyring]
                   [email] [password]

    positional arguments:
      email                 The e-mail address for your Mint.com account
      password              The password for your Mint.com account

    optional arguments:
      -h, --help            show this help message and exit
      --accounts            Retrieve account information (default if nothing else
                            is specified)
      --budgets             Retrieve budget information
      --net-worth           Retrieve net worth (as a single float value)
      --extended-accounts   Retrieve extended account information (slower, implies
                            --accounts)
      --transactions, -t    Retrieve transactions
      --filename FILENAME, -f FILENAME
                            write results to file. can be {csv,json} format.
                            default is to write to stdout.
      --keyring             Use OS keyring for storing password information

    >>> mintapi --keyring email@example.com
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
this repository and run: ``python mintapi/api.py``

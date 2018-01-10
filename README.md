# mintapi

a screen-scraping API for Mint.com. [![Build Status](https://travis-ci.org/mrooney/mintapi.svg?branch=master)](https://travis-ci.org/mrooney/mintapi)

## Installation
Ensure you have Python 2 or 3 and pip (`easy_install pip`) and then:

```shell
pip install mintapi
```

If you do not want to manually find and provide your Mint session cookies, as described below, then please also install `selenium` and `chromedriver`:
```shell
pip install selenium
brew install chromedriver # or sudo apt-get install chromium-chromedriver on Ubuntu/Debian
```

## Usage

### from Python

From python, instantiate the Mint class (from the mintapi package) and you can
make calls to retrieve account/budget information.  We recommend using the
`keyring` library for persisting credentials.

```python
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
  mint.get_transactions_csv(include_investment=False) # as raw csv data
  mint.get_transactions_json(include_investment=False, skip_duplicates=False)

  # Get net worth
  mint.get_net_worth()

  # Initiate an account refresh
  mint.initiate_account_refresh()
```

---
Run it as a sub-process from your favorite language; `pip install mintapi` creates a binary in your $PATH. From the command-line, the output is JSON:

```shell
    usage: mintapi [-h] [--accounts] [--budgets] [--net-worth]
              [--extended-accounts] [--transactions] [--extended-transactions]
              [--start-date [START_DATE]] [--include-investment]
              [--skip-duplicates] [--show-pending] [--filename FILENAME]
              [--keyring] [--session SESSION] [--thx_guid THX_GUID]
              [email] [password]

    positional arguments:
      email                 The e-mail address for your Mint.com account
      password              The password for your Mint.com account

    optional arguments:
      -h, --help            show this help message and exit
      --accounts            Retrieve account information (default if nothing else
                            is specified)
      --budgets             Retrieve budget information
      --net-worth           Retrieve net worth information
      --extended-accounts   Retrieve extended account information (slower, implies
                            --accounts)
      --transactions, -t    Retrieve transactions
      --extended-transactions
                            Retrieve transactions with extra information and
                            arguments
      --start-date [START_DATE]
                            Earliest date for transactions to be retrieved from.
                            Used with --extended-transactions. Format: mm/dd/yy
      --include-investment  Used with --extended-transactions
      --skip-duplicates     Used with --extended-transactions
      --show-pending        Exclude pending transactions from being retrieved.
                            Used with --extended-transactions
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
```

If you need to avoid using pip or setup.py, you can also clone/download
this repository and run: ``python mintapi/api.py``

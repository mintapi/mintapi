# mintapi

a screen-scraping API for Mint.com. [![Build Status](https://travis-ci.org/mrooney/mintapi.svg?branch=master)](https://travis-ci.org/mrooney/mintapi)

## Installation
Ensure you have Python 2 or 3 and pip (`easy_install pip`) and then:

```shell
pip install mintapi
brew cask install chromedriver # or sudo apt-get install chromium-chromedriver on Ubuntu/Debian
```

Note that chromedriver must be version 59+ if you want to use headless mode. If not installing via pip,
make sure to install the `install_requires` dependencies from setup.py yourself.

## Usage

### from the command line

From the command line, the most automated invocation will be:

    python mintapi/api.py --keyring --headless you@example.com

This will store your credentials securely in your system keyring, and use a
headless (invisible) browser to log in and grab the account data. If this triggers
an MFA prompt, you'll be prompted on the command line for your code, which by default
goes to SMS unless you specify `--mfa-method=email`. This will also persist a browser
session in $HOME/.mintapi/session to avoid an MFA in the future, unless you specify `--session-path=None`.

If mfa-method is email and your email host provides IMAP access, you can specify your IMAP login details.
This will automate the retrieval of the MFA code from your email and entering it into Mint.

### from Python

From python, instantiate the Mint class (from the mintapi package) and you can
make calls to retrieve account/budget information.  We recommend using the
`keyring` library for persisting credentials.

```python
  import mintapi
  mint = mintapi.Mint(
    'your_email@web.com',  # Email used to log in to Mint
    'password',  # Your password used to log in to mint
    # Optional parameters
    mfa_method='sms',  # Can be 'sms' (default) or 'email'.
                       # if mintapi detects an MFA request, it will trigger the requested method
                       # and prompt on the command line.
    headless=False,  # Whether the chromedriver should work without opening a
                     # visible window (useful for server-side deployments)
    mfa_input_callback=None,  # A callback accepting a single argument (the prompt)
                              # which returns the user-inputted 2FA code. By default
                              # the default Python `input` function is used.
    session_path=None, # Directory that the Chrome persistent session will be written/read from.
                       # To avoid the 2FA code being asked for multiple times, you can either set
                       # this parameter or log in by hand in Chrome under the same user this runs
                       # as.
    imap_account=None, # account name used to log in to your IMAP server
    imap_password=None, # account password used to log in to your IMAP server
    imap_server=None,  # IMAP server host name
    imap_folder='INBOX',  # IMAP folder that receives MFA email
  )

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

  # Get transactions for a specific account
  accounts = mint.get_accounts(True)
  for account in accounts:
    mint.get_transactions_csv(id=account["id"])
    mint.get_transactions_json(id=account["id"])

  # Get net worth
  mint.get_net_worth()
  
  # Get credit score
  mint.get_credit_score()

  # Initiate an account refresh
  mint.initiate_account_refresh()
```

---
Run it as a sub-process from your favorite language; `pip install mintapi` creates a binary in your $PATH. From the command-line, the output is JSON:

```shell
    usage: mintapi [-h] [--session-path [SESSION_PATH]] [--accounts]
                   [--budgets] [--net-worth] [--extended-accounts] [--transactions]
                   [--extended-transactions] [--credit-score] [--credit-report] [--start-date [START_DATE]]
                   [--include-investment] [--skip-duplicates] [--show-pending]
                   [--filename FILENAME] [--keyring] [--headless]
                   [--mfa-method {sms,email}]
                   [email] [password]

    positional arguments:
      email                 The e-mail address for your Mint.com account
      password              The password for your Mint.com account

    optional arguments:
      -h, --help            show this help message and exit
      --accounts            Retrieve account information (default if nothing else
                            is specified)
      --session-path [SESSION_PATH]
                            Directory to save browser session, including cookies. Used to prevent repeated
                            MFA prompts. Defaults to $HOME/.mintapi/session. Set to None to use a temporary
                            profile.
      --budgets             Retrieve budget information
      --credit-score        Retrieve credit score
      --credit-report       Retrieve full credit report & history
      --net-worth           Retrieve net worth information
      --extended-accounts   Retrieve extended account information (slower, implies --accounts)
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
      --headless            Whether to execute chromedriver with no visible
                            window.
      --mfa-method {sms,email}
                            The MFA method to automate.
      --imap-account IMAP_ACCOUNT
      --imap-password IMAP_PASSWORD
      --imap-server IMAP_SERVER_HOSTNAME
      --imap-folder IMAP_FOLDER
                            Default is INBOX
      --imap-test           Test access to IMAP server

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

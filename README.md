# mintapi

[![Build Status](https://github.com/mintapi/mintapi/actions/workflows/ci.yml/badge.svg)](https://github.com/mintapi/mintapi/actions)
[![PyPI Version](https://img.shields.io/pypi/v/mintapi)](https://pypi.org/project/mintapi/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


An unofficial screen-scraping API for Mint.com.

## IMPORTANT: mintapi 2.0 vs 1.x and breaking changes

We recently released 2.0, which supports (and only supports) the new Mint UI:

 * If your account has the new UI with the nav on the *left*, you'll need to install at least 2.0: `pip install mintapi>=2.0`
 * If your account still has the original UI with the nav on *top*, to use 2.0, you will need to specify `--beta` in your command-line options or submit `beta=True` when initializing the class.  Otherwise, please install the latest 1.x release: `pip install mintapi<2.0`

**Please note** that due to data changes on the Mint.com side as well as various new features and changes on the mintapi side, *there are several breaking changes in 2.0*. Please see [the CHANGELOG](https://github.com/mintapi/mintapi/blob/main/CHANGELOG.md#20) for details.

## Community

Please [join us on Discord](https://discord.gg/YjJEuJRAu9) to get help or just chat with fellow mintapi users :)

## Installation

Ensure you have Python 3 and pip (`easy_install pip`) and then:

```shell
pip install mintapi
```

`mintapi` scrapes Mint.com by navigating a Chrome browser (or Chromium) just as a human would. Once logged in, the API allows programatic access to various Mint REST APIs. Selenium/WebDriver is used to accomplish this, and specifically, ChromeDriver under the hood. `mintapi` will download the latest stable release of chromedriver, unless --use_chromedriver_on_path is given. **NOTE: You must have [Chrome](https://www.google.com/chrome/) or [Chromium](https://www.chromium.org/getting-involved/dev-channel/) installed, on the `stable` track, and be up-to-date!** If you run into a `SessionNotCreatedException` about "ChromeDriver only supports Chrome version XX", you need to [update Chrome](https://support.google.com/chrome/answer/95414).

## Usage

### From the Command Line

From the command line, the most automated invocation will be:

    mintapi --keyring --headless you@example.com

This will store your credentials securely in your system keyring, and use a
headless (invisible) browser to log in and grab the account data. If this triggers
an MFA prompt, you'll be prompted on the command line for your code, which by default
goes to SMS unless you specify `--mfa-method=email`. This will also persist a browser
session in $HOME/.mintapi/session to avoid an MFA in the future, unless you specify `--session-path=None`.

If you wish to simplify the number of arguments passed in the command line, you can use a configuration file by specifying `--config-file`.  For arguments such as `--transactions`, you can add a line in your config file that says `transactions`.  For other arguments that have input, such as `--start-date`, you would add a line such as `start-date=10/01/21`.  There are two exceptions to what you can add to the config file: email and password.  Since these arguments do not include `--`, you cannot add them to the config file.

### Linux Distributions (including Raspberry Pi OS)

If you're running mintapi in a server environment on an automatic schedule, consider running mintapi in headless mode if you don't need to see the login workflow. In addition, you'll want to use your distribution's package manager to install chromium and chromedriver. Make sure your distribution is up-to-date and then install/update Chromium (debian-family example): `apt install chromium-browser chromium-chromedriver`. Then use the option `use_chromedriver_on_path` either through the CLI or the python api so that mintapi doesn't try to find a matching chromedriver.

If you need to download the chromedriver manually, be sure to get the version that matches your chrome version and make the chromedriver available to your python interpreter either by putting the chromedriver in your python working directory or inside your `PATH` as described in the [python selenium documentation](https://www.selenium.dev/selenium/docs/api/py/index.html#drivers).

### General Automation Scenarios

When running this inside of a cron job or other long-term automation scripts, it might be helpful to specify chrome and chromedriver executables so as not to conflict with other chrome versions you may have. Selenium by default just gets these from your `PATH` environment variable, so customizing your environment can force a deterministic behavior from mintapi. To use a different browser besides Chrome or Chromium, see the [python api](#from-python). Below are two examples.

#### Unix Environment

If you wanted to make sure that mintapi used the chromium executable in my /usr/bin directory when executing a cron job, you could write the following cron line:

```cron
0 7 * * FRI PATH=/usr/bin:$PATH mintapi --headless john@example.com my_password
```

where prepending the /usr/bin path to path will make those binaries found first. This will only affect the cron job and will not change the environment for any other process.

#### Windows Environment

You can do a similar thing in windows by executing the following in Powershell.

```powershell
$ENV:PATH = "C:\Program Files\Google\Chrome;$ENV:PATH"
mintapi --headless john@example.com my_password
```

#### Docker Image

You can also use the docker image to help manage your environment so you don't have to worry about chrome or chromedriver versions. There are a few caveats:
1. Headless mode is recommended. GUI works but introduces the need to configure an X11 server which varies with setup. Google is your friend.
2. Almost always use the flag `--use-chromedriver-on-path` as the chrome and chromedriver built into the docker image already match and getting the latest will break the image.
3. If you want to persist credentials or your chrome session, you'll need to do some volume mounting.

To use the image:
```
docker run --rm --shm-size=2g ghcr.io/mintapi/mintapi mintapi john@example.com my_password --headless --use-chromedriver-on-path
```

#### AWS Lambda Environment

AWS Lambda may need a [specific chrome driver with specific options](https://robertorocha.info/setting-up-a-selenium-web-scraper-on-aws-lambda-with-python/). You can initialize Mint with your own pre-configured headless serverless chrome through a constructor:


```python
driver = initialize_serverless_chrome_driver(...)
mint = mintapi.Mint(..., driver=driver)
...
```


### MFA Authentication Methods

As of v2.0, `mfa_method` is only required if your login flow presents you with the option to select which Multifactor Authentication Method you wish to use, typically as a result of your account configured to accept different methods.  

If `mintapi` detects that your Mint account uses IMAP and your email host provides IMAP access, you can specify your IMAP login details.  This will automate the retrieval of the MFA code from your email and entering it into Mint.  If you use IMAP in conjunction with `keyring`, then you can store your IMAP password (`imap-password`) in keyring.  To do so, simply omit `imap-password` and you will initially be prompted for the password associated with your IMAP account.  Then, on subsequent uses of your IMAP account, you will not have to specify your password.

If `mfa-method` is soft-token then you must also pass your `mfa-token`. The `mfa-token` can be obtained by going to [your mint.com settings](https://mint.intuit.com/settings.event?filter=all) and clicking on 'Intuit Account'. From there go to *Sign In & Security* -> *Two-step verification*. From there, enable the top option however you wish (either text or email is fine). After that, start the process to enable the *Authenticator app* option and when you get the part where you see the QR code, **copy the manual setup code** that appears next to it. Careful where you store this as it allows anyone to generate TOTP codes. This is the token that you will pass to `mfa-token` in either the python api or from the command line.

While Mint supports authentication via Voice, `mintapi` does not currently support this option.  Compatability with this method will be added in a later version.

### Multi-Data Support

As of v2.0, mintapi supports returning multiple types of data in one call, such as: `mintapi --accounts --budgets --transactions`.  When exporting multiple data types, you can either send it directly to `stdout` or you can export to a file via `--filename`.  mintapi will create a file for each type of data, with a suffix based on the format.  For example, if you run `mintapi --accounts --transactions --filename=current --format=csv`, then you will receive two files: `current_account.csv` and `current_transaction.csv`.  The following table outlines the option selected and its corresponding suffix:

| Option       | Suffix       |
| -----------  | -----------  |
| accounts     | account      |
| bills        | bills        |
| budgets      | budget       |
| transactions | transaction  |
| trends       | trends       |
| categories   | category     |
| investments  | investment   |
| net-worth    | net_worth    |
| credit-score | credit_score |
| credit-report| credit_report|

### Financial Data Trends

Mint supports providing some analysis of your financial data based on different types of "trends".  Mint's requirements for accessing this data using mintapi is a bit more complex than the other endpoints.

| Parameter         | Data Type          | Description  |
| ----------------  | ------------------ | -----------  |
| report_type       | ReportView.Options | The type of report to generate. |
| date_filter       | DateFilter.Options | The date window to analyze your trends. |
| start_date        | Optional[str]      | An optional beginning date (mm-dd-yy) to your trend analysis. |
| end_date          | Optional[str]      | An optional ending date (mm-dd-yy) to your trend analysis. |
| category_ids      | List[str]          | An optional list of category IDs to include in your trend analysis. |
| tag_ids           | List[str]          | An optional list of tag IDs to include in your trend analysis. |
| descriptions      | List[str]          | An optional list of descriptions to include in your trend analysis. |
| account_ids       | List[str]          | An optional list of account IDs to include in your trend analysis. |
| match_all_filters | boolean            | Whether to match all supplied filters (True) or at least one (False) |
| limit             | int                | The page size of results. |
| offset            | int                | The starting record of your results. |

#### Report Type

As mentioned above, the Report Type is the type of report for which to generate trend analysis.  The supplied value must be one of the following enum values:

| Enum Value | Description |
| ---------- | ----------- |
| 1          | Spending Over Time |
| 2          | Spending by Category |
| 3          | Spending by Merchant |
| 4          | Spending by Tag |
| 5          | Income Over Time |
| 6          | Income by Category |
| 7          | Income by Merchant |
| 8          | Income by Tag |
| 9          | Assets by Type |
| 10         | Assets Over Time |
| 11         | Assets by Account |
| 12         | Debts Over Time |
| 13         | Debts by Type |
| 14         | Debts by Account |
| 15         | Net Worth Over Time |
| 16         | Net Income Over Time |

### Financial Data Transactions

If you want to provide a more granular filtering of your financial data transactions, you can select from a variety of search filters that are sent to Mint. 

| Parameter         | Data Type          | Description  |
| ----------------  | ------------------ | -----------  |
| date_filter       | DateFilter.Options | The date window for which to filter your transactions. |
| start_date        | Optional[str]      | An optional beginning date (mm-dd-yy) to your transaction filtering. |
| end_date          | Optional[str]      | An optional ending date (mm-dd-yy) to your transaction filtering. |
| category_ids      | List[str]          | An optional list of category IDs of transactions to include. |
| tag_ids           | List[str]          | An optional list of tag IDs of transactions to include. |
| descriptions      | List[str]          | An optional list of descriptions of transactions to include. |
| account_ids       | List[str]          | An optional list of account IDs of transactions to include. |
| match_all_filters | boolean            | Whether to match all supplied filters (True) or at least one (False) |
| include_investment | boolean           | Whether to include those transactions that are associated with an Investment Account. |
| remove_pending    | boolean            | Whether to remove those transactions that are still Pending. | 
| limit             | int                | The page size of results. |
| offset            | int                | The starting record of your results. |

### Date Filters

As mentioned above, the Date Filter is the date window for which to generate your trend analysis or for which to search transactions.  The supplied value must be one of the following enum values:

| Enum Value | Description |
| ---------- | ----------- |
| 1          | Last 7 Days |
| 2          | Last 14 Days |
| 3          | This Month   |
| 4          | Last Month   |
| 5          | Last 3 Months |
| 6          | Last 6 Months |
| 7          | Last 7 Months |
| 8          | This Year     |
| 9          | Last Year     |
| 10         | All Time      |
| 11         | Custom        |

If you select a Custom Date Filter, then `start_date` and `end_date` are required fields.  Similarly, if you wish to use `start_date` and `end_date`, Custom Date Filter must be used.

### From Python

From python, instantiate the Mint class (from the mintapi package) and you can
make calls to retrieve account/budget information.  We recommend using the
`keyring` library for persisting credentials.

```python
  import mintapi
  mint = mintapi.Mint(
    'your_email@web.com',  # Email used to log in to Mint
    'password',  # Your password used to log in to mint
    # Optional parameters
    mfa_method='sms',  # See MFA Methods section
                       # Can be 'sms' (default), 'email', or 'soft-token'.
                       # if mintapi detects an MFA request, it will trigger the requested method
                       # and prompt on the command line.
    mfa_input_callback=None,  # see MFA Methods section
                              # can be used with any mfa_method
                              # A callback accepting a single argument (the prompt)
                              # which returns the user-inputted 2FA code. By default
                              # the default Python `input` function is used.
    mfa_token=None,   # see MFA Methods section
                      # used with mfa_method='soft-token'
                      # the token that is used to generate the totp
    intuit_account=None, # account name when multiple accounts are registered with this email.
    headless=False,  # Whether the chromedriver should work without opening a
                     # visible window (useful for server-side deployments)
                         # None will use the default account.
    session_path=None, # Directory that the Chrome persistent session will be written/read from.
                       # To avoid the 2FA code being asked for multiple times, you can either set
                       # this parameter or log in by hand in Chrome under the same user this runs
                       # as.
    imap_account=None, # account name used to log in to your IMAP server
    imap_password=None, # account password used to log in to your IMAP server
    imap_server=None,  # IMAP server host name
    imap_folder='INBOX',  # IMAP folder that receives MFA email
    wait_for_sync=False,  # do not wait for accounts to sync
    wait_for_sync_timeout=300,  # number of seconds to wait for sync
    fail_if_stale=True, # True will raise an exception if Mint is unable to refresh your data.
	use_chromedriver_on_path=False,  # True will use a system provided chromedriver binary that
	                                 # is on the PATH (instead of downloading the latest version)
    driver=None        # pre-configured driver. If None, Mint will initialize the WebDriver.
  )

  # Get account information
  mint.get_account_data()

  # Get budget information
  mint.get_budget_data()

  # Get transactions
  mint.get_transaction_data() # as pandas dataframe

  # Get transactions for a specific account
  accounts = mint.get_account_data()
  for account in accounts:
    mint.get_transaction_data(id=account["id"])

  # Get net worth
  mint.get_net_worth_data()

  # Get credit score
  mint.get_credit_score_data()

  # Get bills
  mint.get_bills()

  # Get investments (holdings and transactions)
  mint.get_investment_data()

  # Close session and exit cleanly from selenium/chromedriver
  mint.close()

  # Initiate an account refresh
  mint.initiate_account_refresh()

  # you can also use mintapi's login in workflow with your own selenium webdriver
  # this will allow for more custom selenium driver setups
  # one caveat is that it must be based on seleniumrequests currently
  # seleniumrequests has most browsers already
  # it also has mixins for any browsers it doesn't have so the sky is the limit!
  from seleniumrequests import Firefox
  mint = mintapi.Mint()
  mint.driver = Firefox()
  mint.status_message, mint.token = mintapi.sign_in(
    email, password, mint.driver, mfa_method=None, mfa_token=None,
    mfa_input_callback=None, intuit_account=None, wait_for_sync=True,
    wait_for_sync_timeout=5 * 60,
    imap_account=None, imap_password=None,
    imap_server=None, imap_folder="INBOX",
  )
  # now you can do all the normal api calls
  # ex:
  mint.get_transaction_data()
```

---
Run it as a sub-process from your favorite language; `pip install mintapi` creates a binary in your $PATH. From the command-line, the output is JSON:

```shell
    usage: mintapi [-h] [--session-path [SESSION_PATH]] [--accounts] [--investments]
                   [--beta] [--budgets | --budget_hist] [--net-worth]
                   [--credit-score] [--credit-report]
                   [--exclude-inquiries] [--exclude-accounts] [--exclude-utilization]
                   [--start-date [START_DATE]] [--end-date [END_DATE]]
                   [--limit] [--include-investment] [--show-pending]
                   [--format] [--filename FILENAME] [--keyring] [--headless]
                   [--mfa-method {sms,email,soft-token}]
                   [--categories] [--attention]
                   [--transactions] [--transaction-date-filter]
                   [--trends] [--trend-report-type] [--trend-date-filter]
                   email [password]

    positional arguments:
      email                 The e-mail address for your Mint.com account (required)
      password              The password for your Mint.com account (if not supplied, --keyring must be provided)

    optional arguments:
      -h, --help            show this help message and exit
      --accounts            Retrieve account information (default if nothing else
                            is specified)
      --session-path [SESSION_PATH]
                            Directory to save browser session, including cookies. Used to prevent repeated
                            MFA prompts. Defaults to $HOME/.mintapi/session. Set to None to use a temporary
                            profile.
      --beta                Use the beta version of Mint
      --budgets             Retrieve budget information for current month
      --budget_hist         Retrieve historical budget information (past 12 months)
      --categories          Retrieve your configured Mint categories
      --config-file, -c     File used to store arguments
      --credit-score        Retrieve credit score
      --credit-report       Retrieve full credit report & history
      --exclude-inquiries   Used in conjunction with --credit-report, ignores credit inquiry data.
      --exclude-accounts    Used in conjunction with --credit-report, ignores credit account data.
      --exclude-utilization Used in conjunction with --credit-report, ignores credit utilization data.
      --net-worth           Retrieve net worth information
      --transactions, -t    Retrieve transactions
      --transaction-date-filter The date window for which to filter your transactions.  Default is All Time.
      --trends              Retrieve trend data related to your financial information
      --trend-report-type   The type of report for which to generate trend analysis.  Default is Spending Over Time.
      --trend-date-filter   The date window for which to generate your trend analysis.  Default is This Month.
      --start-date [START_DATE]
                            Earliest date for which to retrieve transactions.
                            Used with --transactions. Format: mm/dd/yy
      --end-date [END_DATE]
                            Latest date for which to retrieve transactions.
                            Used with --transactions. Format: mm/dd/yy
      --investments         Retrieve data related to your investments, whether they be retirement or         personal stock purchases
      --include-investment  Used with --transactions
      --limit               Number of records to include from the API.  Default is 5000.
      --show-pending        Retrieve pending transactions.
                            Used with --transactions
      --fail-if-stale       At login, Mint attempts to refresh your data.  If you wish to exit when the sync fails, use this option.
      --filename FILENAME, -f FILENAME
                            write results to file. If no file is specified, then data is written to stdout.  Do not specify the file extension as it is determined based on the selection of `--format`.
      --format              Determines the output format of the data, either `csv` or         `json`.  The default value is `json`.  If no `filename` is specified, then this determines the `stdout` format.  Otherwise, if a `filename` is specified, then this determines the file extension.
      --keyring             Use OS keyring for storing password information
      --headless            Whether to execute chromedriver with no visible
                            window.
	  --use-chromedriver-on-path
	  						Whether to use the chromedriver on PATH, instead of
              			  	downloading a local copy.
      --mfa-method {sms,email,soft-token}
                            The MFA method to automate.
      --mfa-token      The base32 encoded MFA token.
      --imap-account IMAP_ACCOUNT
      --imap-password IMAP_PASSWORD
      --imap-server IMAP_SERVER_HOSTNAME
      --imap-folder IMAP_FOLDER
                            Default is INBOX
      --imap-test           Test access to IMAP server
      --no_wait_for_sync    Do not wait for accounts to sync
      --wait_for_sync_timeout
                            Number of seconds to wait for sync (default is 300)
      --attention.          Get notice if there are any accounts that need attention


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

### Special Considerations

#### Email\Account Access

Because of the inter-connected nature of Intuit's products, when signing in to Mint for one account, you may see accounts associated with Intuit products other than Mint.  If you do have multiple Intuit accounts, you should be aware that if one email is associated with two different usernames (and multiple Intuit products, such as TurboTax or Quickbooks), you may receive a prompt for Multifactor Authentication, even with a saved session.  One possible solution is separating the two accounts to use two different emails.  For many email clients, you can route different email addresses to the same account by using a suffix.  For example, you could have email addresses "myaccount+mint@gmail.com" and "myaccount+quickbooks@gmail.com" and receive emails for both in the "myaccount@gmail.com" inbox.

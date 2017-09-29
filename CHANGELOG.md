1.28
---
- fix get_transactions_json when start_date predates all transactions (thanks @jprouty!)

1.27
---
- fix NoneType error when getting cookies via chromedriver (thanks @dherg!)

1.26
---
- properly display messages when webdriver raises a URLError (thanks @dherg!)

1.25
---
- use Excel-compatible datetime formatting and allow customizing (thanks @felciano!)

1.24
---
- fix "Unknown" categories when categories in budgets (thanks @drunnells!)

1.23
---
- mintapi raises MintException instead of Exception for better exception
  handling when used as a library (thanks @titilambert!)

1.22
---
- more robustly match content types (thanks @jbms!)
- eliminate an unnecessary use of pandas (thanks @jbms!)

1.21
---
- import fix for python3

1.20
---
- automate cookie grabbing w/ selenium+chromedriver (thanks @matthewwardrop!)
- allow passing in required cookies via CLI/API
- update README to cover the cookies now required
- --include-investments now works with --transactions (thanks @felciano)

1.19
---
- updated URLs for intuit.com domain change
- added command-line switch for --session=ius_session_cookie

1.18
---
- add the ability to get extended transaction information from the command line,
  along with all its options

1.17
---
- fix get_transactions_json to work with Mint change (github#57),
  thanks @dtiz!

1.16
---
- allow specifying a start date for get_transactions_json
- add get_detailed_transactions which converts the json to a pandas
  dataframe, adds the year to all transactions, and reverses credit
  activity.

1.15
---
- fix urllib3 import exception on Ubuntu/Debian, thanks @dancudds!

1.14
---
- fix json output when using --filename
- flake8 fixes

1.13
---
- new get_net_worth / --net-worth options, thanks @wendlinga!

1.12
---
- get_transactions_csv and get_transactions_json API methods

1.11
---
- fix get_budgets with nested categories

1.10.2
---
- re-release to actually include the intended changes from 1.10.1

1.10.1
---
- fix for get_transactions with Python 3
- more helpful error message when pandas is missing

1.9
---
- keyring is lazily required, now compatible with systems where keyring
  module is not available
- PEP8

1.8
---
- fix retrieving transactions (-t)

1.7
---
- -u / --user option to save and grab password from keyring

1.6
---
- -t / --transactions option to fetch transactions
- -f / --filename to write results to csv/json

1.5
---
- various changes to fix and improve scraping Mint.com

1.4
---
- fix Python 3 compat
- add an 'InDate' for each timestamp field that is the date as a
  python-native datetime object
- add unit test / travis integration for the above

1.3.2
---
- fix setup.py for pip installations

1.3
---
- specify SSLv3 to fix making HTTPS requests to Mint on certain Linux systems

1.2
---
- turn into a pypi package. now use `import mintapi` from python or the `mintapi` binary.

1.1
---
- fix login/authentication issue after Mint.com change

1.0
---
- initial release

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

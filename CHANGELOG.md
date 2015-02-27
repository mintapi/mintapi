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

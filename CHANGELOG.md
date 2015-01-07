1.5
---
- Support getting transactions
- No longer use insecure SSLv3
-


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

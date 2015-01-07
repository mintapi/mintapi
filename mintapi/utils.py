# coding=utf-8
from datetime import datetime, date
import random
import re
import time


def get_rnd():
    return str(int(time.mktime(datetime.now().timetuple()))) + str(random.randrange(999)).zfill(3)


BAD_CHAR_RE = re.compile('[\$,%]')


def parse_float(text):
    text = BAD_CHAR_RE.sub('', text)

    try:
        return float(text)
    except ValueError:
        return None


def convert_account_timestamps_to_python_dates(account):
    date_key = [
        'addAccountDate',
        'closeDate',
        'fiLastUpdated',
        'lastUpdated',
    ]
    for date_key in date_key:
        # Convert from javascript timestamp to unix timestamp
        # http://stackoverflow.com/a/9744811/5026
        try:
            ts = account[date_key] / 1e3
        except TypeError:
            # returned data is not a number, don't parse
            continue
        except LookupError:
            # value does not exist
            continue
        account[date_key + '_ts'] = account[date_key]
        account[date_key] = datetime.datetime.fromtimestamp(ts)


def convert_mint_transaction_dates_to_python_dates(transaction):
    date_keys = ['date', 'odate']
    for date_key in date_keys:
        transaction[date_key + '_str'] = transaction[date_key]
        try:
            transaction[date_key] = datetime.strptime(transaction[date_key] + ' ' + str(date.today().year), '%b %d %Y')
        except ValueError:
            transaction[date_key] = datetime.strptime(transaction[date_key], '%m/%d/%y')
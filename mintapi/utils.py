# coding=utf-8
import datetime
import random
import re
import time


def get_rnd(cls):
    return str(int(time.mktime(datetime.datetime.now().timetuple()))) + str(random.randrange(999)).zfill(3)

BAD_CHAR_RE = re.compile('[\$,%]')
def parse_float(text):
    text = BAD_CHAR_RE.sub('', text)

    try:
        return float(text)
    except ValueError:
        return None

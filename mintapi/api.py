import json
import requests
import ssl

from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

DATE_FIELDS = [
    'addAccountDate',
    'closeDate',
    'fiLastUpdated',
    'lastUpdated',
]


class MintHTTPSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, **kwargs):
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, ssl_version=ssl.PROTOCOL_SSLv3, **kwargs)

def get_accounts(email, password):
    # 1: Login.
    session = requests.Session()
    session.mount('https://', MintHTTPSAdapter())

    if session.get("https://wwws.mint.com/login.event?task=L").status_code != requests.codes.ok:
        raise Exception("Failed to load Mint main page '{}'".format(Mint.START_URL))
    
    data = {"username": email, "password": password, "task": "L", "browser": "firefox", "browserVersion": "27", "os": "linux"}
    headers = {"accept": "application/json"}
    response = session.post("https://wwws.mint.com/loginUserSubmit.xevent", data=data, headers=headers).text
    if "token" not in response:
        raise Exception("Mint.com login failed[1]")

    response = json.loads(response)
    if not response["sUser"]["token"]:
        raise Exception("Mint.com login failed[2]")

    # 2: Grab token.
    token = response["sUser"]["token"]

    # 3. Issue service request.
    request_id = "42" # magic number? random number?
    data = {"input": json.dumps([
        {"args": {
            "types": [
                "BANK", 
                "CREDIT", 
                "INVESTMENT", 
                "LOAN", 
                "MORTGAGE", 
                "OTHER_PROPERTY", 
                "REAL_ESTATE", 
                "VEHICLE", 
                "UNCLASSIFIED"
            ]
        }, 
        "id": request_id, 
        "service": "MintAccountService", 
        #"task": "getAccountsSorted"
        "task": "getAccountsSortedByBalanceDescending"
        }
    ])}
    response = session.post("https://wwws.mint.com/bundledServiceController.xevent?legacy=false&token="+token, data=data, headers=headers).text
    if request_id not in response:
        raise Exception("Could not parse account data: " + response)
    response = json.loads(response)
    accounts = response["response"][request_id]["response"]

    # Return datetime objects for dates
    for account in accounts:
        for df in DATE_FIELDS:
            if df in account:
                # Convert from javascript timestamp to unix timestamp
                # http://stackoverflow.com/a/9744811/5026
                ts = account[df] / 1e3
                account[df + 'InDate'] = datetime.fromtimestamp(ts)

    return accounts

def main():
    import getpass
    import sys

    # Handle Python 3's raw_input change.
    try: input = raw_input
    except NameError: pass

    if len(sys.argv) >= 3:
        email, password = sys.argv[1:]
    else:
        email = input("Mint email: ")
        password = getpass.getpass("Password: ")

    accounts = get_accounts(email, password)
    print(json.dumps(accounts, indent=2))
    
if __name__ == "__main__":
    main()

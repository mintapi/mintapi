import json
import requests

def get_accounts(email, password):
    # 1: Login.
    session = requests.Session()

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
    return accounts

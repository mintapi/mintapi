import json
from pyquery import PyQuery as pq
import requests

def get_accounts(email, password):
    # 1: Login.
    session = requests.Session()
    data = {"username": email, "password": password, "task": "L", "nextPage": ""}
    response = session.post("https://wwws.mint.com/loginUserSubmit.xevent", data=data).text
    if "javascript-token" not in response.lower():
        raise Exception("Mint.com login failed")

    # 2: Grab token.
    d = pq(response.encode("utf-8"))
    token = d("input#javascript-token")[0].value

    # 3. Issue service request.
    request_id = "115485" # magic number? random number?
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
        "task": "getAccountsSorted"}
    ])}
    response = session.post("https://wwws.mint.com/bundledServiceController.xevent?token="+token, data=data)
    response = json.loads(response.text)["response"]
    accounts = response[request_id]["response"]
    return accounts

if __name__ == "__main__":
    import getpass, sys

    if len(sys.argv) >= 3:
        email, password = sys.argv[1:]
    else:
        email = raw_input("Mint email: ")
        password = getpass.getpass("Password: ")

    accounts = get_accounts(email, password)
    print json.dumps(accounts, indent=2)


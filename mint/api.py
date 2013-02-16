from cookielib import CookieJar, DefaultCookiePolicy
import json
import urllib2, urllib

from pyquery import PyQuery as pq

def enable_cookies():
    cj = CookieJar(DefaultCookiePolicy(rfc2965=True))
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    urllib2.install_opener(opener)

def url_get(url, postVars=None):
    try:
        con = urllib2.urlopen(url, postVars)
    except Exception:
        result = None
    else:
        result = con.read()

    return result

def url_post(url, varDict):
    return url_get(url, urllib.urlencode(varDict))

def get_accounts(email, password):
    enable_cookies()
    # login
    post_args = {"username": email, "password": password, "task": "L", "nextPage": ""}
    response = url_post("https://wwws.mint.com/loginUserSubmit.xevent", post_args)
    if "javascript-token" not in response.lower():
        raise Exception("Mint.com login failed")

    # grab token
    d = pq(response)
    token = d("input#javascript-token")[0].value

    # issue service request
    request_id = "115485" # magic number? random number?
    post_args = {"input": json.dumps([
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
    json_response = url_post("https://wwws.mint.com/bundledServiceController.xevent?token="+token, post_args)
    response = json.loads(json_response)["response"]

    # turn into correct format
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


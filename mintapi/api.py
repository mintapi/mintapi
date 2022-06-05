from mintapi.browser import SeleniumBrowser


class Mint(SeleniumBrowser):
    # For now keep the signature unchanged as the selenium browser
    # TODO: change this class to accept a passed cookie or instantiate a browser session
    # only to extract a cookie then use the REST client
    pass


def get_accounts(email, password, get_detail=False):
    mint = Mint(email, password)
    return mint.get_account_data(get_detail=get_detail)


def get_net_worth(email, password):
    mint = Mint(email, password)
    account_data = mint.get_account_data()
    return mint.get_net_worth(account_data)


def get_budgets(email, password):
    mint = Mint(email, password)
    return mint.get_budgets()


def get_credit_score(email, password):
    mint = Mint(email, password)
    return mint.get_credit_score()


def get_credit_report(email, password):
    mint = Mint(email, password)
    return mint.get_credit_report()


def initiate_account_refresh(email, password):
    mint = Mint(email, password)
    return mint.initiate_account_refresh()

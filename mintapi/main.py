# coding=utf-8
import datetime
import json

from .api import Mint

def make_accounts_presentable(accounts):
    for account in accounts:
        for k, v in account.items():
            if isinstance(v, datetime.datetime):
                account[k] = repr(v)
    return accounts


def print_accounts(accounts):
    print(json.dumps(make_accounts_presentable(accounts), indent=2))

def main():
    import getpass
    import optparse

    # Parse command-line arguments {{{
    cmdline = optparse.OptionParser(usage='usage: %prog [options] email password')
    cmdline.add_option('--accounts', action='store_true', dest='accounts', default=False, help='Retrieve account information (default if nothing else is specified)')
    cmdline.add_option('--budgets', action='store_true', dest='budgets', default=False, help='Retrieve budget information')
    cmdline.add_option('--extended-accounts', action='store_true', dest='accounts_ext', default=False, help='Retrieve extended account information (slower, implies --accounts)')

    (options, args) = cmdline.parse_args()

    # Handle Python 3's raw_input change.
    try:
        input = raw_input
    except NameError:
        pass

    if len(args) >= 2:
        (email, password) = args[0:1]
    else:
        email = input("Mint email: ")
        password = getpass.getpass("Password: ")

    if options.accounts_ext:
        options.accounts = True

    if not (options.accounts or options.budgets):
        options.accounts = True

    mint = Mint(email, password)

    data = None
    if options.accounts and options.budgets:
        try:
            accounts = make_accounts_presentable(mint.get_accounts(get_detail=options.accounts_ext))
        except:
            accounts = None

        try:
            budgets = mint.get_budgets()
        except:
            budgets = None

        data = {'accounts': accounts, 'budgets': budgets}
    elif options.budgets:
        try:
            data = mint.get_budgets()
        except:
            data = None
    elif options.accounts:
        try:
            data = make_accounts_presentable(mint.get_accounts(get_detail=options.accounts_ext))
        except:
            data = None

    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()

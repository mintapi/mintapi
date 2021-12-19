import atexit
import logging
import os
import sys
import json
from datetime import datetime
import getpass

import keyring
import configargparse

from mintapi.api import Mint
from mintapi.signIn import get_email_code

logger = logging.getLogger("mintapi")


def parse_arguments(args):
    ARGUMENTS = [
        (
            ("email",),
            {
                "nargs": "?",
                "default": None,
                "help": "The e-mail address for your Mint.com account",
            },
        ),
        (
            ("password",),
            {
                "nargs": "?",
                "default": None,
                "help": "The password for your Mint.com account",
            },
        ),
        (
            ("--accounts",),
            {
                "action": "store_true",
                "dest": "accounts",
                "default": False,
                "help": "Retrieve account information (default if nothing else is specified)",
            },
        ),
        (
            ("--attention",),
            {
                "action": "store_true",
                "help": "Display accounts that need attention (None if none).",
            },
        ),
        (
            ("--budgets",),
            {
                "action": "store_true",
                "dest": "budgets",
                "default": False,
                "help": "Retrieve budget information",
            },
        ),
        (
            ("--budget_hist",),
            {
                "action": "store_true",
                "dest": "budget_hist",
                "default": None,
                "help": "Retrieve 12-month budget history information",
            },
        ),
        (
            ("--categories",),
            {
                "action": "store_true",
                "default": False,
                "help": "Retrieve category definitions as configured in Mint",
            },
        ),
        (
            ("--chromedriver-download-path",),
            {
                "default": os.getcwd(),
                "help": "The directory to download chromedrive to.",
            },
        ),
        (
            ("--config-file", "-c"),
            {
                "required": False,
                "is_config_file": True,
                "help": "The path to the config file used.",
            },
        ),
        (
            ("--credit-report",),
            {
                "action": "store_true",
                "dest": "credit_report",
                "default": False,
                "help": "Retrieve full credit report",
            },
        ),
        (
            ("--credit-score",),
            {
                "action": "store_true",
                "dest": "credit_score",
                "default": False,
                "help": "Retrieve current credit score",
            },
        ),
        (
            ("--end-date",),
            {
                "nargs": "?",
                "default": None,
                "help": "Latest date for transactions to be retrieved from. Used with --transactions or --extended-transactions. Format: mm/dd/yy",
            },
        ),
        (
            ("--extended-accounts",),
            {
                "action": "store_true",
                "dest": "accounts_ext",
                "default": False,
                "help": "Retrieve extended account information (slower, implies --accounts)",
            },
        ),
        (
            ("--exclude-accounts",),
            {
                "action": "store_true",
                "default": False,
                "help": "When accessing credit report details, exclude data related to credit accounts.  Used with --credit-report.",
            },
        ),
        (
            ("--exclude-inquiries",),
            {
                "action": "store_true",
                "default": False,
                "help": "When accessing credit report details, exclude data related to credit inquiries.  Used with --credit-report.",
            },
        ),
        (
            ("--exclude-utilization",),
            {
                "action": "store_true",
                "default": False,
                "help": "When accessing credit report details, exclude data related to credit utilization.  Used with --credit-report.",
            },
        ),
        (
            ("--extended-transactions",),
            {
                "action": "store_true",
                "default": False,
                "help": "Retrieve transactions with extra information and arguments",
            },
        ),
        (
            ("--filename", "-f"),
            {
                "help": "write results to file. can be {csv,json} format. default is to write to stdout."
            },
        ),
        (
            ("--headless",),
            {
                "action": "store_true",
                "help": "Whether to execute chromedriver with no visible window.",
            },
        ),
        (("--imap-account",), {"default": None, "help": "IMAP login account"}),
        (("--imap-folder",), {"default": "INBOX", "help": "IMAP folder"}),
        (("--imap-password",), {"default": None, "help": "IMAP login password"}),
        (("--imap-server",), {"default": None, "help": "IMAP server"}),
        (
            ("--imap-test",),
            {"action": "store_true", "help": "Test imap login and retrieval."},
        ),
        (
            ("--investments",),
            {
                "action": "store_true",
                "default": False,
                "help": "Retrieve data related to your investments, whether they be retirement or personal stock purchases",
            },
        ),
        (
            ("--include-investment",),
            {
                "action": "store_true",
                "default": False,
                "help": "Used with --extended-transactions",
            },
        ),
        (
            ("--keyring",),
            {
                "action": "store_true",
                "help": "Use OS keyring for storing password information",
            },
        ),
        (
            ("--mfa-method",),
            {
                "choices": ["sms", "email", "soft-token"],
                "default": "sms",
                "help": "The MFA method to automate.",
            },
        ),
        (
            ("--mfa-token",),
            {"default": None, "help": "The MFA soft-token to pass to oathtool."},
        ),
        (
            ("--net-worth",),
            {
                "action": "store_true",
                "dest": "net_worth",
                "default": False,
                "help": "Retrieve net worth information",
            },
        ),
        (
            ("--no_wait_for_sync",),
            {
                "action": "store_true",
                "default": False,
                "help": "By default, mint api will wait for accounts to sync with the backing financial institutions. If this flag is present, do not wait for them to sync.",
            },
        ),
        (
            ("--session-path",),
            {
                "nargs": "?",
                "default": os.path.join(os.path.expanduser("~"), ".mintapi", "session"),
                "help": "Directory to save browser session, including cookies. Used to prevent repeated MFA prompts. Defaults to $HOME/.mintapi/session.  Set to None to use a temporary profile.",
            },
        ),
        # Displayed to the user as a postive switch, but processed back here as a negative
        (
            ("--show-pending",),
            {
                "action": "store_false",
                "default": True,
                "help": "Exclude pending transactions from being retrieved. Used with --extended-transactions",
            },
        ),
        (
            ("--skip-duplicates",),
            {
                "action": "store_true",
                "default": False,
                "help": "Used with --extended-transactions",
            },
        ),
        (
            ("--start-date",),
            {
                "nargs": "?",
                "default": None,
                "help": "Earliest date for transactions to be retrieved from. Used with --transactions or --extended-transactions. Format: mm/dd/yy",
            },
        ),
        (
            ("--transactions", "-t"),
            {"action": "store_true", "default": False, "help": "Retrieve transactions"},
        ),
        (
            ("--use-chromedriver-on-path",),
            {
                "action": "store_true",
                "help": "Whether to use the chromedriver on PATH, instead of downloading a local copy.",
            },
        ),
        (
            ("--wait_for_sync_timeout",),
            {
                "type": int,
                "default": 5 * 60,
                "help": "Number of seconds to wait for sync.  Default is 5 minutes",
            },
        ),
    ]

    # Parse command-line arguments {{{
    cmdline = configargparse.ArgumentParser()

    for argument_commands, argument_options in ARGUMENTS:
        cmdline.add_argument(*argument_commands, **argument_options)

    return cmdline.parse_args(args)


def make_accounts_presentable(accounts, presentable_format="EXCEL"):
    formatter = {
        "DATE": "%Y-%m-%d",
        "ISO8601": "%Y-%m-%dT%H:%M:%SZ",
        "EXCEL": "%Y-%m-%d %H:%M:%S",
    }[presentable_format]

    for account in accounts:
        for k, v in account.items():
            if isinstance(v, datetime):
                account[k] = v.strftime(formatter)
    return accounts


def print_accounts(accounts):
    print(json.dumps(make_accounts_presentable(accounts), indent=2))


def handle_password(type, prompt, email, password, use_keyring=False):
    if use_keyring and not password:
        # If we don't yet have a password, try prompting for it
        password = keyring.get_password(type, email)

    if not password:
        # If we still don't have a password, prompt for it
        password = getpass.getpass("Mint password: ")

    if use_keyring:
        # If keyring option is specified, save the password in the keyring
        keyring.set_password(type, email, password)

    return password


def validate_file_extensions(options):
    if any(
        [
            options.transactions,
            options.extended_transactions,
        ]
    ):
        if not any(
            [
                options.filename is None,
                options.filename.endswith(".csv"),
                options.filename.endswith(".json"),
            ]
        ):
            raise ValueError(
                "File extension must be either .csv or .json for transaction data"
            )
    else:
        if not any([options.filename is None, options.filename.endswith(".json")]):
            raise ValueError("File extension must be .json for non-transaction data")


def output_data(options, data, attention_msg=None):
    # output the data
    if options.transactions or options.extended_transactions:
        if options.filename is None:
            print(data.to_json(orient="records"))
        elif options.filename.endswith(".csv"):
            data.to_csv(options.filename, index=False)
        elif options.filename.endswith(".json"):
            data.to_json(options.filename, orient="records")
    else:
        if options.filename is None:
            print(json.dumps(data, indent=2))
        elif options.filename.endswith(".json"):
            with open(options.filename, "w+") as f:
                json.dump(data, f, indent=2)

    if options.attention:
        if attention_msg is None or attention_msg == "":
            attention_msg = "no messages"
        if options.filename is None:
            print(attention_msg)
        else:
            with open(options.filename, "w+") as f:
                f.write(attention_msg)


def main():
    options = parse_arguments(sys.argv[1:])

    # Try to get the e-mail and password from the arguments
    email = options.email
    password = options.password
    imap_account = options.imap_account
    imap_password = options.imap_password
    mfa_method = options.mfa_method

    validate_file_extensions(options)

    if not email:
        # If the user did not provide an e-mail, prompt for it
        email = input("Mint e-mail: ")

    password = handle_password(
        "mintapi", "Mint password: ", email, password, options.keyring
    )

    if mfa_method == "email" and imap_account:
        imap_password = handle_password(
            "mintapi_imap",
            "IMAP password: ",
            imap_account,
            imap_password,
            options.keyring,
        )

    if options.accounts_ext:
        options.accounts = True

    if not any(
        [
            options.accounts,
            options.budgets,
            options.transactions,
            options.extended_transactions,
            options.net_worth,
            options.credit_score,
            options.credit_report,
            options.investments,
            options.attention,
            options.categories,
        ]
    ):
        options.accounts = True

    if options.session_path == "None":
        session_path = None
    else:
        session_path = options.session_path

    mint = Mint(
        email,
        password,
        mfa_method=mfa_method,
        mfa_token=options.mfa_token,
        session_path=session_path,
        headless=options.headless,
        imap_account=imap_account,
        imap_password=imap_password,
        imap_server=options.imap_server,
        imap_folder=options.imap_folder,
        wait_for_sync=not options.no_wait_for_sync,
        wait_for_sync_timeout=options.wait_for_sync_timeout,
        use_chromedriver_on_path=options.use_chromedriver_on_path,
        chromedriver_download_path=options.chromedriver_download_path,
    )
    atexit.register(mint.close)  # Ensure everything is torn down.

    if options.imap_test:
        mfa_code = get_email_code(
            imap_account,
            imap_password,
            options.imap_server,
            imap_folder=options.imap_folder,
            delete=False,
        )
        print("MFA CODE:", mfa_code)
        sys.exit()

    data = None
    if options.accounts and options.budgets:
        try:
            accounts = make_accounts_presentable(
                mint.get_accounts(get_detail=options.accounts_ext)
            )
        except Exception:
            accounts = None

        try:
            budgets = mint.get_budgets()
        except Exception:
            budgets = None

        data = {"accounts": accounts, "budgets": budgets}
    elif options.budgets:
        try:
            data = mint.get_budgets()
        except Exception:
            data = None
    elif options.budget_hist:
        try:
            data = mint.get_budgets(hist=12)
        except Exception:
            data = None
    elif options.accounts:
        try:
            data = make_accounts_presentable(
                mint.get_accounts(get_detail=options.accounts_ext)
            )
        except Exception:
            data = None
    elif options.transactions:
        data = mint.get_transactions(
            start_date=options.start_date,
            end_date=options.end_date,
            include_investment=options.include_investment,
        )
    elif options.extended_transactions:
        data = mint.get_detailed_transactions(
            start_date=options.start_date,
            end_date=options.end_date,
            include_investment=options.include_investment,
            remove_pending=options.show_pending,
            skip_duplicates=options.skip_duplicates,
        )
    elif options.categories:
        data = mint.get_categories()
    elif options.investments:
        data = mint.get_investment_data()
    elif options.net_worth:
        data = mint.get_net_worth()
    elif options.credit_score:
        data = mint.get_credit_score()
    elif options.credit_report:
        data = mint.get_credit_report(
            details=True,
            exclude_inquiries=options.exclude_inquiries,
            exclude_accounts=options.exclude_accounts,
            exclude_utilization=options.exclude_utilization,
        )

    if options.attention:
        attention_msg = mint.get_attention()
    output_data(options, data, attention_msg)

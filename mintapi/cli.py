import atexit
import logging
import os
import sys
import json
import getpass
from mintapi import constants
import keyring
import configargparse
from mintapi.trends import ReportView
from mintapi.filters import DateFilter
from mintapi.api import Mint
from mintapi.signIn import get_email_code
from pandas import json_normalize

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
            ("--beta",),
            {
                "action": "store_true",
                "default": False,
                "help": "Use the beta version of Mint",
            },
        ),
        (
            ("--bills",),
            {
                "action": "store_true",
                "dest": "bills",
                "default": False,
                "help": "Retrieve bills",
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
                "help": "Latest date for transactions to be retrieved from. Used with --transactions. Format: mm/dd/yy",
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
            ("--fail-if-stale",),
            {
                "action": "store_true",
                "default": False,
                "help": "At login, Mint attempts to refresh your data.  If you wish to exit when the sync fails, use this option.",
            },
        ),
        (
            ("--filename", "-f"),
            {
                "help": "write results to file. can be {csv,json} format. default is to write to stdout."
            },
        ),
        (
            ("--format",),
            {
                "choices": [constants.JSON_FORMAT, constants.CSV_FORMAT],
                "default": constants.JSON_FORMAT,
                "help": "The format used to return data.",
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
            ("--intuit-account",),
            {
                "default": None,
                "help": "Specify an override of the default intuit account for accessing Mint",
            },
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
                "help": "Used with --transactions",
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
            ("--limit",),
            {
                "type": int,
                "default": 5000,
                "help": "Number of records to include from the API.  Default is 5000.",
            },
        ),
        (
            ("--mfa-method",),
            {
                "choices": [
                    constants.MFA_VIA_SMS,
                    constants.MFA_VIA_EMAIL,
                    constants.MFA_VIA_SOFT_TOKEN,
                ],
                "default": None,
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
                "help": "Retrieve pending transactions. Used with --transactions",
            },
        ),
        (
            ("--start-date",),
            {
                "nargs": "?",
                "default": None,
                "help": "Earliest date for transactions to be retrieved from. Used with --transactions. Format: mm/dd/yy",
            },
        ),
        (
            ("--transaction-date-filter",),
            {
                "type": int,
                "default": DateFilter.Options.ALL_TIME,
                "dest": "transaction_date_filter",
                "help": "The date window for which to generate your transaction search.  Default is All Time.",
            },
        ),
        (
            ("--transactions", "-t"),
            {"action": "store_true", "default": False, "help": "Retrieve transactions"},
        ),
        (
            ("--trends",),
            {
                "action": "store_true",
                "dest": "trends",
                "default": False,
                "help": "Retrieve trend data related to your financial information",
            },
        ),
        (
            ("--trend-report-type",),
            {
                "type": int,
                "default": ReportView.Options.SPENDING_TIME,
                "dest": "trend_report_type",
                "help": "The type of report for which to generate trend analysis.  Default is Spending Over Time.",
            },
        ),
        (
            ("--trend-date-filter",),
            {
                "type": int,
                "default": DateFilter.Options.THIS_MONTH,
                "dest": "trend_date_filter",
                "help": "The date window for which to generate your trend analysis.  Default is This Month.",
            },
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


def handle_password(type, prompt, email, password, use_keyring=False):
    if use_keyring and not password:
        # If we don't yet have a password, try prompting for it
        password = keyring.get_password(type, email)

    if not password:
        # If we still don't have a password, prompt for it
        password = getpass.getpass(prompt)

    if use_keyring:
        # If keyring option is specified, save the password in the keyring
        keyring.set_password(type, email, password)

    return password


def format_filename(options, type):
    if options.filename is None:
        filename = None
    else:
        filename = "{}_{}.{}".format(options.filename, type.lower(), options.format)
    return filename


def output_data(options, data, type, attention_msg=None):
    filename = format_filename(options, type)
    if filename is None:
        if options.format == constants.CSV_FORMAT:
            print(json_normalize(data).to_csv(index=False))
        else:
            print(json.dumps(data, indent=2))
        # NOTE: While this logic is here, unless validate_file_extensions
        #       allows for other data types to export to CSV, this will
        #       only include investment data.
    elif options.format == constants.CSV_FORMAT:
        # NOTE: Currently, investment_data, which is a flat JSON, is the only
        #       type of data that uses this section.  So, if we open this up to
        #       other non-flat JSON data, we will need to revisit this.
        json_normalize(data).to_csv(filename, index=False)
    elif options.format == constants.JSON_FORMAT:
        with open(filename, "w+") as f:
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
    report_type = ReportView.Options(options.trend_report_type)
    trend_date_filter = DateFilter.Options(options.trend_date_filter)
    transaction_date_filter = DateFilter.Options(options.transaction_date_filter)

    if not email:
        # If the user did not provide an e-mail, prompt for it
        email = input("Mint e-mail: ")

    password = handle_password(
        "mintapi", "Mint password: ", email, password, options.keyring
    )

    if imap_account:
        imap_password = handle_password(
            "mintapi_imap",
            "IMAP password: ",
            imap_account,
            imap_password,
            options.keyring,
        )

    if not any(
        [
            options.accounts,
            options.bills,
            options.budgets,
            options.transactions,
            options.trends,
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
        intuit_account=options.intuit_account,
        wait_for_sync=not options.no_wait_for_sync,
        wait_for_sync_timeout=options.wait_for_sync_timeout,
        fail_if_stale=options.fail_if_stale,
        use_chromedriver_on_path=options.use_chromedriver_on_path,
        chromedriver_download_path=options.chromedriver_download_path,
        beta=options.beta,
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

    attention_msg = None
    if options.attention:
        attention_msg = mint.get_attention()

    if options.trends:
        data = mint.get_trend_data(
            report_type=report_type,
            date_filter=trend_date_filter,
            start_date=options.start_date,
            end_date=options.end_date,
            category_ids=None,
            tag_ids=None,
            descriptions=None,
            account_ids=None,
            match_all_filters=True,
            limit=options.limit,
            offset=0,
        )
        output_data(options, data, constants.TRENDS_KEY, attention_msg)

    if options.accounts:
        data = mint.get_account_data(limit=options.limit)
        output_data(options, data, constants.ACCOUNT_KEY, attention_msg)

    if options.bills:
        data = mint.get_bills()
        output_data(options, data, constants.BILL_KEY, attention_msg)

    if options.budgets:
        data = mint.get_budget_data(limit=options.limit)
        output_data(options, data, constants.BUDGET_KEY, attention_msg)
    elif options.budget_hist:
        data = mint.get_budget_data(limit=options.limit, hist=12)
        output_data(options, data, constants.BUDGET_KEY, attention_msg)

    if options.transactions:
        data = mint.get_transaction_data(
            date_filter=transaction_date_filter,
            start_date=options.start_date,
            end_date=options.end_date,
            category_ids=None,
            tag_ids=None,
            descriptions=None,
            account_ids=None,
            match_all_filters=True,
            include_investment=options.include_investment,
            remove_pending=options.show_pending,
            limit=options.limit,
            offset=0,
        )
        output_data(options, data, constants.TRANSACTION_KEY, attention_msg)

    if options.categories:
        data = mint.get_category_data(
            limit=options.limit,
        )
        output_data(options, data, constants.CATEGORY_KEY, attention_msg)

    if options.investments:
        data = mint.get_investment_data(
            limit=options.limit,
        )
        output_data(options, data, constants.INVESTMENT_KEY, attention_msg)

    if options.net_worth:
        data = mint.get_net_worth_data()
        formatted_data = {"net_worth": data}
        output_data(options, formatted_data, constants.NET_WORTH_KEY, attention_msg)

    if options.credit_score:
        data = mint.get_credit_score_data()
        formatted_data = {"credit_score": data}
        output_data(options, formatted_data, constants.CREDIT_SCORE_KEY, attention_msg)

    if options.credit_report:
        data = mint.get_credit_report_data(
            details=True,
            exclude_inquiries=options.exclude_inquiries,
            exclude_accounts=options.exclude_accounts,
            exclude_utilization=options.exclude_utilization,
        )
        output_data(options, data, constants.CREDIT_REPORT_KEY, attention_msg)

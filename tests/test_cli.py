import tempfile
import unittest

from mintapi.cli import format_filename, parse_arguments
from mintapi.constants import ACCOUNT_KEY, TRANSACTION_KEY


class CLIOutputTests(unittest.TestCase):
    def test_config_file(self):
        # verify parsing from config file
        config_file = write_transactions_file()
        arguments = parse_arguments_file(config_file)
        self.assertEqual(arguments.transactions, True)
        config_file.close()

    def test_format_filename(self):
        config_file = write_transactions_file()
        arguments = parse_arguments_file(config_file)
        name = TRANSACTION_KEY.lower()
        filename = format_filename(arguments, name)
        self.assertEqual(filename, "current_{}.csv".format(name))

        config_file = write_accounts_file()
        arguments = parse_arguments_file(config_file)
        name = ACCOUNT_KEY.lower()
        filename = format_filename(arguments, name)
        self.assertEqual(filename, "current_{}.json".format(name))

        config_file = write_investments_file()
        arguments = parse_arguments_file(config_file)
        filename = format_filename(arguments, None)
        self.assertEqual(filename, None)


def write_transactions_file():
    config_file = tempfile.NamedTemporaryFile(mode="wt")
    config_file.write("transactions\nformat=csv\nfilename=current")
    return config_file


def write_accounts_file():
    config_file = tempfile.NamedTemporaryFile(mode="wt")
    config_file.write("accounts\nformat=json\nfilename=current")
    return config_file


def write_investments_file():
    config_file = tempfile.NamedTemporaryFile(mode="wt")
    config_file.write("investments")
    return config_file


def parse_arguments_file(config_file):
    config_file.flush()
    return parse_arguments(["-c", config_file.name])


if __name__ == "__main__":
    unittest.main()

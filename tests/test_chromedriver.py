import unittest

import requests
from mintapi.signIn import (
    CHROME_ZIP_TYPES,
    get_chrome_driver_url,
    get_latest_chrome_driver_version,
)


class ChromedriverTests(unittest.TestCase):
    def test_chrome_driver_links(self):
        latest_version = get_latest_chrome_driver_version()
        for platform in CHROME_ZIP_TYPES:
            request = requests.get(get_chrome_driver_url(latest_version, platform))
            self.assertEqual(request.status_code, 200)


if __name__ == "__main__":
    unittest.main()

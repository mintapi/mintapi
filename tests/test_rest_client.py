"""
Rest client tests

Focuses on client instantiation and request construction - not endpoint data
"""
import unittest

import pytest
from mintapi.rest import RESTClient


class RestAuthTests(unittest.TestCase):
    def test_header_updates(self):
        pass

    def test_cookie_updates(self):
        pass


class RestRequestHandlingTests(unittest.TestCase):
    def test_request_param_passing(self):
        pass

    def test_response_status_checking(self):
        pass

    def test_pagination_call(self):
        pass


class RestEndpointTests(unittest.TestCase):
    """
    E2E rest endpoint test with mock endpoint responses
    (endpoint logic tested separately)
    """


if __name__ == "__main__":
    pytest.main()

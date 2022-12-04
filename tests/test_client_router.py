"""
Tests for the main Mint class

Verifies routing and instantiation in the presence of auth params
between browser and rest client - no endpoint testing
"""
import unittest

import pytest


class MintApiTests(unittest.TestCase):
    def test_initialization_with_auth_headers(self):
        pass

    def test_initialization_without_auth_headers(self):
        pass

    def test_auth_transfer(self):
        pass

    def test_method_routing_with_rest_client(self):
        pass

    def test_method_routing_without_rest_client(self):
        pass

    def test_method_routing_with_nonsense_method(self):
        pass


if __name__ == "__main__":
    pytest.main()

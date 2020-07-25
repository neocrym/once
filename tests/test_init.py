"""Tests for once/__init__.py."""

import unittest

import once


class TestUniqueName(unittest.TestCase):
    """Test the :func:`once.unique_name` function."""

    def test_unique_name(self):
        """Test that the :func:`unique_name` works."""
        self.assertEqual(once.unique_name(unittest), "unittest")
        self.assertEqual(once.unique_name(once.unique_name), "once.unique_name")
        self.assertEqual(once.unique_name(None), "NoneType")
        self.assertEqual(once.unique_name(self), "tests.test_init.TestUniqueName")
        self.assertEqual(
            once.unique_name(self.test_unique_name),
            "tests.test_init.TestUniqueName.test_unique_name",
        )

from util.wait_random import wait_random
import pytest
from unittest.mock import patch
from unittest import TestCase


class TestWaitRandom(TestCase):
    @patch("util.wait_random.sleep", return_value=None)
    def test_wait_random(self, patched_sleep):
        SUT = wait_random(100)
        self.assertEqual(1, patched_sleep.call_count)
        assert SUT is None

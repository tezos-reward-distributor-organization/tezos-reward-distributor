import sys
import unittest
from enum import Enum
from log_config import main_logger
from util.exit_program import ExitCode, exit_program


class TestExitProgram(unittest.TestCase):
    def test_exit_program(self):
        with self.assertRaises(SystemExit) as context:
            exit_program(ExitCode.SUCCESS, "SUCCESS")
        self.assertEqual(context.exception.code, ExitCode.SUCCESS.value)

        with self.assertRaises(SystemExit) as context:
            exit_program(ExitCode.GENERAL_ERROR, "GENERAL_ERROR")
        self.assertEqual(context.exception.code, ExitCode.GENERAL_ERROR.value)

        with self.assertRaises(SystemExit) as context:
            exit_program(ExitCode.USER_ABORT, "USER_ABORT")
        self.assertEqual(context.exception.code, ExitCode.USER_ABORT.value)

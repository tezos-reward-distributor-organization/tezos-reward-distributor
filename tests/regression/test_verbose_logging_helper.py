import os
import shutil
import logging
from unittest import TestCase

from src.log_config import FORMATTER
from src.verbose_logging_helper import VerboseLoggingHelper


class TestVerboseLoggingHelper(TestCase):
    def setUp(self):
        self.keep_at_most = 3
        self.logging_dir = os.path.join(
            os.path.join(os.path.abspath("."), ".."), "logs"
        )
        self.backup_dir = os.path.join(self.logging_dir, "verbose_backup")

        if os.path.isdir(self.logging_dir):
            shutil.rmtree(self.logging_dir)

        os.makedirs(self.logging_dir, exist_ok=True)

        for log_file in self.get_log_files(self.logging_dir):
            os.remove(log_file)

        self.assertTrue(len(self.get_log_files(self.logging_dir)) == 0)
        self.main_logger = logging.getLogger("main")
        self.verbose_logging_helper = VerboseLoggingHelper(
            self.logging_dir,
            True,
            logging.getLogger("verbose"),
            self.main_logger,
            FORMATTER,
            self.keep_at_most,
            "init",
        )
        self.verbose_logging_helper.get_logger().debug("verbose logger started")

        self.assertTrue(len(self.get_log_files(self.logging_dir)) == 1)

    def tearDown(self) -> None:
        self.verbose_logging_helper.close_current_handler()

    def get_log_files(self, path):
        if not os.path.isdir(path):
            return []
        return [
            os.path.join(path, f)
            for f in os.listdir(path)
            if VerboseLoggingHelper.is_log_file(f)
        ]

    def get_archive_files(self, path):
        if not os.path.isdir(path):
            return []
        return [
            os.path.join(path, f)
            for f in os.listdir(path)
            if VerboseLoggingHelper.is_archive_file(f)
        ]

    def test_reset(self):
        cycle = 10
        backup_log_files = self.get_archive_files(self.backup_dir)

        self.verbose_logging_helper.reset(cycle)
        self.verbose_logging_helper.get_logger().debug("verbose logger: cycle 10")

        log_files = self.get_log_files(self.logging_dir)
        self.assertTrue(len(log_files) == 1)

        self.assertTrue(os.path.basename(log_files[0]).startswith("app_verbose"))
        self.assertTrue(os.path.basename(log_files[0]).endswith(".log"))
        self.assertTrue(str(cycle) in os.path.basename(log_files[0]))

        backup_log_files_after_reset = self.get_archive_files(self.backup_dir)
        self.assertEqual(len(backup_log_files) + 1, len(backup_log_files_after_reset))

        self.verbose_logging_helper.reset(cycle + 1)
        self.verbose_logging_helper.reset(cycle + 2)
        self.verbose_logging_helper.reset(cycle + 3)
        self.verbose_logging_helper.reset(cycle + 4)
        self.verbose_logging_helper.reset(cycle + 5)

        self.assertEqual(
            len(self.get_archive_files(self.backup_dir)), self.keep_at_most
        )

    def test_is_archive_file(self):
        self.assertTrue(
            self.verbose_logging_helper.is_archive_file(
                "app_verbose_init_20200101000000.gz"
            )
        )
        self.assertTrue(
            self.verbose_logging_helper.is_archive_file(
                "app_verbose_10_20200101000000.gz"
            )
        )
        self.assertFalse(
            self.verbose_logging_helper.is_archive_file(
                "app_verbose_init_20200101000000.log"
            )
        )
        self.assertFalse(
            self.verbose_logging_helper.is_archive_file(
                "app_log_init_20200101000000.gz"
            )
        )

    def test_is_log_file(self):
        self.assertTrue(
            self.verbose_logging_helper.is_log_file(
                "app_verbose_init_20200101000000.log"
            )
        )
        self.assertTrue(
            self.verbose_logging_helper.is_log_file("app_verbose_10_20200101000000.log")
        )
        self.assertFalse(
            self.verbose_logging_helper.is_log_file(
                "app_verbose_init_20200101000000.gz"
            )
        )
        self.assertFalse(
            self.verbose_logging_helper.is_log_file("app_log_init_20200101000000.log")
        )

    def test_get_log_file_path(self):
        cycle = 12
        cycle12_log_file_path = self.verbose_logging_helper.get_log_file_path(cycle)
        self.assertTrue(
            self.verbose_logging_helper.is_log_file(
                os.path.basename(cycle12_log_file_path)
            )
        )
        self.assertTrue(str(cycle) in os.path.basename(cycle12_log_file_path))

    def test_archive(self):
        log_file_path_before = self.verbose_logging_helper.get_current_log_file_path()
        self.verbose_logging_helper.close_current_handler()
        self.verbose_logging_helper.archive(log_file_path_before)

        archive_file_base_names = [
            os.path.splitext(os.path.basename(f))[0]
            for f in self.get_archive_files(self.backup_dir)
        ]

        self.assertTrue(
            os.path.splitext(os.path.basename(log_file_path_before))[0]
            in archive_file_base_names
        )

    def test_remove_oldest(self):
        pass

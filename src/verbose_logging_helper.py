import gzip
import logging
import os
from datetime import datetime
import shutil


class VerboseLoggingHelper:
    def __init__(
        self,
        logging_dir,
        enabled,
        verbose_logger,
        main_logger,
        formatter,
        keep_at_most,
        mode,
    ):
        self.main_logger = main_logger
        self.logging_dir = logging_dir
        self.formatter = formatter
        self.logger = verbose_logger
        self.logger.setLevel(logging.DEBUG)
        self.keep_at_most = keep_at_most
        self.enabled = enabled
        self.log_file_path = None
        self.handler = None

        if self.enabled:
            self.archive_old_log_file()
            self.change_file_handler(mode)
        else:
            self.set_to_null_handler()

    def set_to_null_handler(self):
        self.log_file_path = None
        self.handler = logging.NullHandler()
        self.logger.addHandler(self.handler)

    def change_file_handler(self, mode):
        self.log_file_path = self.get_log_file_path(mode)
        self.handler = logging.FileHandler(self.log_file_path, "a")
        self.handler.setLevel(logging.DEBUG)
        self.handler.setFormatter(self.formatter)
        self.main_logger.addHandler(self.handler)
        self.logger.addHandler(self.handler)

    def archive_old_log_file(self):
        for file_base_name in os.listdir(self.logging_dir):
            if self.is_log_file(file_base_name):
                self.archive(os.path.join(self.logging_dir, file_base_name))

    @staticmethod
    def is_archive_file(base_name):
        return base_name.endswith(".gz") and base_name.startswith("app_verbose_")

    @staticmethod
    def is_log_file(base_name):
        return base_name.endswith(".log") and base_name.startswith("app_verbose_")

    def get_log_file_path(self, cycle):
        formatted_date = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(
            self.logging_dir, f"app_verbose_{cycle}_{formatted_date}.log"
        )

    def reset(self, cycle):
        if not self.enabled:
            return

        self.close_current_handler()
        old_path = self.log_file_path
        self.change_file_handler(cycle)

        self.archive(old_path)

    def close_current_handler(self):
        self.logger.removeHandler(self.handler)
        self.main_logger.removeHandler(self.handler)
        self.handler.close()

    def archive(self, path):
        archive_dir = os.path.join(self.logging_dir, "verbose_backup")
        os.makedirs(archive_dir, exist_ok=True)

        archive_file = os.path.join(
            archive_dir, os.path.splitext(os.path.basename(path))[0] + ".gz"
        )

        with open(path, "rb") as f_in:
            with gzip.open(archive_file, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        os.remove(path)

        self.remove_oldest(archive_dir)

    def remove_oldest(self, archive_dir):
        while True:
            files = [
                os.path.join(archive_dir, f)
                for f in os.listdir(archive_dir)
                if self.is_archive_file(f)
            ]
            sorted_files = sorted(files, key=os.path.getmtime)

            if len(sorted_files) <= self.keep_at_most:
                break  # Exit the loop if the number of files is within the limit

            os.remove(sorted_files[0])  # Remove the oldest file

    def get_logger(self):
        return self.logger

    def get_current_log_file_path(self):
        return self.log_file_path

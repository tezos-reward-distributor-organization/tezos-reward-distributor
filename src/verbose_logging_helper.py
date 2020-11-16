import logging
import os
from datetime import datetime
from zipfile import ZipFile


class VerboseLoggingHelper:
    def __init__(self, logging_dir, enabled, logger, formatter, keep_at_most=3):
        self.logging_dir = logging_dir
        self.formatter = formatter
        self.logger = logger
        self.logger.setLevel(logging.DEBUG)
        self.keep_at_most = keep_at_most
        self.archive_old_log_file()

        if enabled:
            self.log_file_path = self.get_log_file_path('init')
            self.handler = logging.FileHandler(self.log_file_path, 'a')
        else:
            self.log_file_path = None
            self.handler = logging.NullHandler()

        self.logger.addHandler(self.handler)

    def archive_old_log_file(self):
        for file_name in os.listdir(self.logging_dir):
            if file_name.endswith(".log") and file_name.startswith("app_verbose_"):
                self.archive(os.path.join(self.logging_dir, file_name))

    def get_log_file_path(self, cycle):
        formatted_date = datetime.now().strftime("%Y%m%d%H%M%S")
        return os.path.join(self.logging_dir, f'app_verbose_{cycle}_{formatted_date}.log')

    def reset(self, cycle):
        self.logger.removeHandler(self.handler)
        old_path = self.log_file_path
        self.log_file_path = self.get_log_file_path(cycle)
        self.handler = logging.FileHandler(self.log_file_path, 'a')
        self.logger.addHandler(self.handler)

        self.archive(old_path)

    def archive(self, path):
        archive_dir = os.path.join(self.logging_dir, 'verbose_backup')
        os.makedirs(archive_dir, exist_ok=True)

        archive_file = os.path.join(archive_dir, os.path.splitext(os.path.basename(path))[0] + '.zip')

        with ZipFile(archive_file, 'w') as arch_zip:
            arch_zip.write(path, arcname=os.path.basename(path))
        os.remove(path)

        self.remove_oldest(archive_dir)

    def remove_oldest(self, archive_dir):
        sorted_files = sorted(filter(os.path.isfile, os.listdir(archive_dir)), key=os.path.getmtime)
        print(archive_dir)
        print(sorted_files)
        print(len(sorted_files))
        print(self.keep_at_most)
        print(len(sorted_files) > self.keep_at_most)
        print(sorted_files[-1])

        if len(sorted_files) > self.keep_at_most:
            os.remove(sorted_files[-1])

    def get_logger(self):
        return self.logger

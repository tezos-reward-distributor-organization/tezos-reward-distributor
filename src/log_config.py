import os
import logging
from logging.handlers import RotatingFileHandler

main_logger = logging.getLogger('main')
main_logger.setLevel(logging.DEBUG)

# create file handler which logs even debug messages
# fh = logging.FileHandler('logs/app.log')
max_log_size = 5 * 1024 * 1024  # Bytes
log_file_path = os.path.abspath('logs/app.log')
log_dir = os.path.dirname(log_file_path)
os.makedirs(log_dir, exist_ok=True)

fh = RotatingFileHandler(log_file_path, maxBytes=max_log_size, backupCount=10)
fh.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(threadName)-9s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# add the handlers to logger
main_logger.addHandler(ch)
main_logger.addHandler(fh)


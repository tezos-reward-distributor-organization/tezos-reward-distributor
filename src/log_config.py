import logging
import os
from logging.handlers import RotatingFileHandler
from Constants import DEFAULT_LOG_FILE, BASE_DIR
from verbose_logging_helper import VerboseLoggingHelper


FORMATTER = logging.Formatter(
    "%(asctime)s - %(threadName)-9s - %(levelname)s - %(message)s"
)

main_logger = logging.getLogger("main")
verbose_logger = logging.getLogger("verbose")

verbose_log_helper = VerboseLoggingHelper(
    os.path.expanduser(
        os.path.join(os.path.normpath(BASE_DIR), os.path.normpath(DEFAULT_LOG_FILE))
    ),
    False,
    verbose_logger,
    main_logger,
    FORMATTER,
    100,
    "OFF",
)


def get_verbose_log_helper():
    return verbose_log_helper


def init(
    log_to_syslog=False,
    log_file=os.path.expanduser(
        os.path.join(os.path.normpath(BASE_DIR), os.path.normpath(DEFAULT_LOG_FILE))
    ),
    init_verbose=False,
    keep_at_most=60,
    mode="init",
):
    main_logger.setLevel(logging.DEBUG)

    # create file handler which logs even debug messages
    max_log_size = 5 * 1024 * 1024  # Bytes
    log_file_path = os.path.expanduser(os.path.normpath(log_file))
    log_dir = os.path.dirname(log_file_path)
    os.makedirs(log_dir, exist_ok=True)
    fh = RotatingFileHandler(log_file_path, maxBytes=max_log_size, backupCount=10)
    fh.setLevel(logging.DEBUG)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # create formatter and add it to the handlers
    ch.setFormatter(FORMATTER)
    fh.setFormatter(FORMATTER)

    # add the handlers to logger
    main_logger.addHandler(ch)
    main_logger.addHandler(fh)

    if log_to_syslog:
        syslog_handler = logging.handlers.SysLogHandler(address="/dev/log")
        main_logger.addHandler(syslog_handler)

    global verbose_log_helper
    verbose_log_helper = VerboseLoggingHelper(
        log_dir,
        init_verbose,
        verbose_logger,
        main_logger,
        FORMATTER,
        keep_at_most,
        mode,
    )

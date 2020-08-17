import sqlite3
from threading import Lock
from log_config import main_logger

logger = main_logger


class Storage:

    dbPath = ""
    dryRun = False
    dbh = None
    locker = None

    def __init__(self, _dbPath, _dryRun=False):

        self.dryRun = _dryRun
        self.dbPath = "{}drd_config{}.sqlite".format(_dbPath, "_dryRun" if self.dryRun else "")
        self.locker = Lock()

        logger.info("Storage - Database located at {}{}".format(
            self.dbPath, " (Dry Run)" if self.dryRun else ""))

    @staticmethod
    def get_config_db_path(config_dir):

        config_file = None
        files = os.listdir(config_dir)

        if len(files) > 1:
            raise ConfigStorageException(
                "Application only supports one baking configuration. Found at least 2 in {}".format(config_dir))

        if len(files) == 0:
            raise ConfigStorageException(
                "Unable to find configuration database in '{}'".format(config_dir))

        config_file = os.path.join(config_dir, file[0])

        return config_file

    def __enter__(self):
        try:
            self.locker.acquire()
            self.dbh = sqlite3.connect(self.dbPath, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
            logger.info("Storage - Opened '{}'".format(self.dbPath))
        except sqlite3.Error as e:
            logger.warn("Storage - SQLite Error: {}".format(e))
        return self.dbh

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type:
            # logger.debug("Storage - EXCEPTION {}: {}".format(exc_type, exc_value))
            self.dbh.rollback()
        else:
            self.dbh.commit()

        self.dbh.close()
        self.locker.release()

        logger.info("Storage - Closed")

    def __del__(self):
        if self.dbh:
            self.dbh.close()
        logger.info("Storage - Database Connection Closed")


class StorageException(Exception):
    pass

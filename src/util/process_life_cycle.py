import signal
from _signal import SIGABRT, SIGILL, SIGSEGV, SIGTERM

from util.lock_file import LockFile
from log_config import main_logger

logger = main_logger


class ProcessLifeCycle:
    def __init__(self, ):
        self.lock_file = LockFile()
        self.running = False
        self.lock_taken = False

    def start(self, lock):
        for sig in (SIGABRT, SIGILL, SIGSEGV, SIGTERM):
            signal.signal(sig, self.stop_handler)
        if lock:
            self.lock_file.lock()
            self.lock_taken = True
        self.running = True

    def stop(self):
        logger.info("--------------------------------------------------------")
        logger.info("Sensitive operations are in progress!")
        logger.info("Please wait while the application is being shut down!")
        logger.info("--------------------------------------------------------")
        if self.lock_taken:
            self.lock_file.release()
            logger.info("Lock file removed!")
        self.running = False

    def is_running(self):
        return self.running

    def stop_handler(self, signum, frame):
        logger.info("Application stop handler called: {}".format(signum))
        self.stop()

import signal
from _signal import SIGABRT, SIGILL, SIGSEGV, SIGTERM

from LockFile import LockFile
from logconfig import main_logger

logger = main_logger

class ProcessLifeCycle:
    def __init__(self, ):
        self.lock_file = LockFile()
        self.running = False

    def start(self):
        for sig in (SIGABRT, SIGILL, SIGSEGV, SIGTERM):
            signal.signal(sig, self.stop_handler)

        self.lock_file.lock()
        self.running = True

    def stop(self):
        logger.info("Please wait while the application is being shut down!")

        self.lock_file.release()
        logger.info("Lock file removed!")
        self.running = False

    def is_running(self):
        return self.running

    def stop_handler(self, signum, frame):
        logger.info("Application stop handler called: {}",signum)
        self.stop()

import signal
from _signal import SIGABRT, SIGILL, SIGSEGV, SIGTERM

from fysom import FysomGlobalMixin, FysomGlobal

from util.lock_file import LockFile
from log_config import main_logger

logger = main_logger


class ProcessLifeCycle(FysomGlobalMixin):
    GSM = FysomGlobal(
        events=[('warn', 'green', 'yellow'),
                {
                    'name': 'panic',
                    'src': ['green', 'yellow'],
                    'dst': 'red',
                    'cond': [  # can be function object or method name
                        'is_angry',  # by default target is "True"
                        {True: 'is_very_angry', 'else': 'yellow'}
                    ]
                },
                ('calm', 'red', 'yellow'),
                ('clear', 'yellow', 'green')],
        initial='green',
        final='red',
        state_field='state'
    )

    def __init__(self):
        self.lock_file = LockFile()
        self.running = False
        self.lock_taken = False
        super(ProcessLifeCycle, self).__init__()

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

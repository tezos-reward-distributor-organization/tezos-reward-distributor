import os


class LockFile:
    def __init__(self):
        self.lock_file_path = "./lock"
        self.lock_acquired = False

    def lock(self):
        self.tryLock()

        pid = os.getpid()
        with open(self.lock_file_path, 'w') as f:
            f.write(str(pid))

        self.lock_acquired = True

    def tryLock(self):
        if self.lock_acquired is False and os.path.isfile(self.lock_file_path):
            raise Exception("Lock file present. Another process is running...")

    def release(self):
        os.remove(self.lock_file_path)

        self.lock_acquired = False

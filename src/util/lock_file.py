import os
import sys
from Constants import CONFIG_DIR


class LockFile:
    def __init__(self, args):
        config_dir = os.path.expanduser(
            os.path.join(self.args.base_directory + CONFIG_DIR)
        )
        self.lock_file_path = os.path.join(config_dir, "lock")
        self.lock_acquired = False

    def lock(self):
        self.tryLock()

        pid = os.getpid()
        try:
            with open(self.lock_file_path, "w") as f:
                f.write(str(pid))
        except Exception as e:
            import errno

            print("Exception during write operation invoked: {}".format(e))
            if e.errno == errno.ENOSPC:
                print("Not enough space on device!")
            exit()

        self.lock_acquired = True

    def tryLock(self):
        if self.lock_acquired is False and os.path.isfile(self.lock_file_path):
            print("Lock file present. Please check if another process is running.")
            for i in range(3):
                print(
                    "Are you sure that no other process is running and want to force the app start process? (y/n)"
                )
                user_input = input()
                if user_input.lower() == "y":
                    self.release()
                    break
                elif user_input.lower() == "n" or i == 2:
                    sys.exit()

    def release(self):
        os.remove(self.lock_file_path)

        self.lock_acquired = False

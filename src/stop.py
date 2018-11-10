import os
import signal
import errno
import time


def main():
    print("Stopping reward distributer")

    stop()

    time.sleep(1)


# taken from https://stackoverflow.com/questions/568271/how-to-check-if-there-exists-a-process-with-a-given-pid-in-python
def pid_exists(pid):
    """Check whether pid exists in the current process table.
    UNIX only.
    """
    if pid < 0:
        return False
    if pid == 0:
        # According to "man 2 kill" PID 0 refers to every process
        # in the process group of the calling process.
        # On certain systems 0 is a valid PID but we have no way
        # to know that in a portable fashion.
        raise ValueError('invalid PID 0')
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH)
            raise
    else:
        return True


def stop():
    pid = None
    try:
        with open("./lock", 'rt') as f:
            pid = f.readline()
            pid = int(pid)
    except FileNotFoundError:
        print("No lock file. No running process")
        return

    if not pid_exists(pid):
        os.remove("./lock")
        return

    os.kill(pid, signal.SIGTERM)

    while pid_exists(pid):
        print("Stopping ...")
        time.sleep(1)

    print("Application with pid {} is stopped!".format(pid))


if __name__ == '__main__':
    main()

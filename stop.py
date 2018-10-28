import os
import signal

def main():
    print("Stopping reward distributer")

    pid=None
    with open("./lock", 'rt') as f:
        pid = f.readline()
        pid = int(pid)

    os.kill(pid, signal.SIGTERM)

if __name__ == '__main__':

    main()

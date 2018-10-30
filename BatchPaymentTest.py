import os
import subprocess

from ClientConfiguration import COMM_HASH, COMM_COUNTER, COMM_PROT, COMM_FORGE
from NetworkConfiguration import network_config_map


def run_and_last_line(cmd):
    my_env = os.environ.copy()
    my_env["TEZOS_CLIENT_UNSAFE_DISABLE_DISCLAIMER"] = "Y"

    network_config = network_config_map["ZERONET"]
    cmd = cmd.replace("%network%", network_config['NAME'].lower())
    print(cmd)
    process = subprocess.Popen(cmd, shell=True,
                               stdout=subprocess.PIPE, env=my_env, bufsize=1, universal_newlines=True)
    line = None
    for l in process.stdout:
        line = l.strip().strip("\"")
    process.wait()
    return line


hash = run_and_last_line(COMM_HASH)
counter = int(run_and_last_line(COMM_COUNTER))
protocol = run_and_last_line(COMM_PROT)
protocol = protocol.strip("]").strip().strip("\"")
bytes = run_and_last_line(COMM_FORGE)

print("hash is {}".format(hash))
print("counter is {}".format(counter))
print("protocol is {}".format(protocol))
print("bytes is {}".format(bytes))

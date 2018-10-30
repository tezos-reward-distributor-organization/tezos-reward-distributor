import os
import subprocess

from ClientConfiguration import COMM_HASH

os.environ["TEZOS_CLIENT_UNSAFE_DISABLE_DISCLAIMER"] = "Y"

from NetworkConfiguration import network_config_map

network_config = network_config_map["ZERONET"]
process = subprocess.Popen(COMM_HASH.replace("%network%", network_config['NAME'].lower()), shell=True, stdout=subprocess.PIPE)

while process.poll() is None:
    output = process.stdout.readline()
    print(output),

process.wait()
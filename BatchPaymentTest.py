import subprocess
from subprocess import call
from ClientConfiguration import COMM_HASH, SHELL_COMM_DISABLE_DISCLAIMER

# call(SHELL_COMM_DISABLE_DISCLAIMER)
from NetworkConfiguration import network_config_map

network_config = network_config_map["ZERONET"]
process = subprocess.Popen(COMM_HASH.replace("%network%", network_config['NAME'].lower()), shell=True, stdout=subprocess.PIPE)
process.wait()
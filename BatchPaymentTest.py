import subprocess
from subprocess import call
from ClientConfiguration import COMM_HASH, SHELL_COMM_DISABLE_DISCLAIMER

# call(SHELL_COMM_DISABLE_DISCLAIMER)

process = subprocess.Popen(COMM_HASH, shell=True, stdout=subprocess.PIPE)
process.wait()
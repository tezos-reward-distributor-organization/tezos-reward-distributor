import os
import subprocess

from ClientConfiguration import COMM_HASH, COMM_COUNTER, COMM_PROT, COMM_FORGE, COMM_SIGN, COMM_PREAPPLY
from NetworkConfiguration import network_config_map


def run_and_last_line(cmd, print_flag=False):
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
        if print_flag:
            print(line)
    process.wait()
    return line


source="tz1YZReTLamLhyPLGSALa4TbMhjjgnSi2cqP"
destionation="tz1MWTkFRXA2dwez4RHJWnDWziLpaN6iDTZ9"
amount=10000
hash = run_and_last_line(COMM_HASH,True)
print()
print("hash is {}".format(hash))

counter = int(run_and_last_line(COMM_COUNTER,True))
print("counter is {}".format(counter))
counter = counter + 1
print()

#protocol = run_and_last_line(COMM_PROT)
#protocol = protocol.strip("]").strip().strip("\"")
protocol = "ProtoALphaALphaALphaALphaALphaALphaALphaALphaDdp3zK"
print()
print("protocol is {}".format(protocol))
print()

bytes = run_and_last_line(COMM_FORGE.replace("%COUNTER%",str(counter)).replace("%BRANCH%",hash).replace("%SOURCE%",source).replace("%DESTINATION%",destionation).replace("%AMOUNT%",amount),True)
print()
print("bytes is {}".format(bytes))
print()

signed = run_and_last_line(COMM_SIGN.replace("%BYTES%",bytes),True)
signed=signed.replace("Signature:","").strip()
print()
print("signed is {}".format(signed))
print()

applied = run_and_last_line(COMM_PREAPPLY.replace("%PROTOCOL%",protocol).replace("%SIGNATURE%",signed).replace("%BRANCH%",hash).replace("%COUNTER%",str(counter)),True)
print()
print("applied is {}".format(applied))
print()







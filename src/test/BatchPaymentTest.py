import os
import base58
import subprocess

from ClientConfiguration import COMM_HASH, COMM_COUNTER, COMM_PROT, COMM_FORGE, COMM_SIGN, COMM_PREAPPLY, COMM_INJECT, \
    CONTENT
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
destionation2="KT1LrDLvDUrkXAEsHzkZLrWHPwnphgL1zSjc"
amount=10000
amount2=1000
hash = run_and_last_line(COMM_HASH,True)
print()
print("hash is {}".format(hash))

counter = int(run_and_last_line(COMM_COUNTER,True))
print("counter is {}".format(counter))

print()

#protocol = run_and_last_line(COMM_PROT)
#protocol = protocol.strip("]").strip().strip("\"")
protocol = "ProtoALphaALphaALphaALphaALphaALphaALphaALphaDdp3zK"
print()
print("protocol is {}".format(protocol))
print()
counter = counter + 1
contant1=CONTENT.replace("%SOURCE%",source).replace("%DESTINATION%",destionation).replace("%AMOUNT%",str(amount)).replace("%COUNTER%",str(counter))
counter = counter + 1
contant2=CONTENT.replace("%SOURCE%",source).replace("%DESTINATION%",destionation2).replace("%AMOUNT%",str(amount2)).replace("%COUNTER%",str(counter))
content=contant1+','+contant2
bytes = run_and_last_line(COMM_FORGE.replace("%BRANCH%",hash).replace("%CONTENT%",content),True)
print()
print("bytes is {}".format(bytes))
print()

signed = run_and_last_line(COMM_SIGN.replace("%BYTES%",bytes),True)
signed=signed.replace("Signature:","").strip()
print()
print("signed is {}".format(signed))
print()

applied = run_and_last_line(COMM_PREAPPLY.replace("%PROTOCOL%",protocol).replace("%SIGNATURE%",signed).replace("%BRANCH%",hash).replace("%CONTENT%",content),True)
print()
print("applied is {}".format(applied))
print()


#decoded=base58.b58decode(b'edsigtnNiJnMTHgUSbASAVbUFiG96whWqrzZ5tw4tsfCxJu55J9wQ1BkQjSncTYhapuwWgE5unpSBhcT5eenaj1fQZni3WvW3jD').hex()
decoded=base58.b58decode(signed).hex()

print("decoded is {}".format(decoded))
decoded_edsig_signature=decoded.replace("09f5cd8612","")[:-8]
print("decoded_edsig_signature is {}".format(decoded_edsig_signature))
signed_operation_bytes=bytes+decoded_edsig_signature
print("signed_operation_bytes is {}".format(signed_operation_bytes))


injected = run_and_last_line(COMM_INJECT.replace("%OPERATION_HASH%",signed_operation_bytes),True)
print("injected is {}".format(injected))


import subprocess

from log_config import main_logger

logger = main_logger

class RegularPayer():
    def __init__(self,client_path,key_name):
        super(RegularPayer,self).__init__()
        self.client_path = client_path
        self.key_name=key_name
        self.transfer_command=self.client_path+" transfer {0:f} from {1} to {2} --fee 0"

    def pay(self,payment_item):
        pymnt_addr = payment_item["address"]
        pymnt_amnt = payment_item["payment"]
        pymnt_cycle = payment_item["cycle"]
        type = payment_item["type"]

        if pymnt_amnt <= 0:
            logger.debug("Reward payment command not executed for %s because reward is 0", pymnt_addr)
            return True

        cmd = self.transfer_command.format(pymnt_amnt, self.key_name, pymnt_addr)

        logger.debug("Reward payment attempt for cycle %s address %s amount %f tz type %s", pymnt_cycle,
                     pymnt_addr, pymnt_amnt, type)

        logger.debug("Reward payment command '{}'".format(cmd))

        # execute client
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        process.wait()

        return True
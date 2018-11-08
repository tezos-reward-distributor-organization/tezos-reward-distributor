from log_config import main_logger
from util.client_utils import send_request, check_response, get_operation_hash

logger = main_logger


class RegularPayer():
    def __init__(self, client_path, key_name):
        super(RegularPayer, self).__init__()
        self.client_path = client_path
        self.key_name = key_name
        self.transfer_command = self.client_path + " transfer {0:f} from {1} to {2} --fee 0"

    def pay(self, payment_item, verbose=None, dry_run=None):
        pymnt_addr = payment_item["address"]
        pymnt_amnt = payment_item["payment"]
        pymnt_cycle = payment_item["cycle"]
        type = payment_item["type"]

        if pymnt_amnt <= 0:
            logger.debug("Reward payment command not executed for %s because reward is 0", pymnt_addr)
            return True

        cmd = self.transfer_command.format(pymnt_amnt, self.key_name, pymnt_addr)

        # if dry run, add -D switch to trigger client --dry-run
        if dry_run: cmd = cmd + " -D"

        logger.debug("Reward payment attempt for cycle %s address %s amount %f tz type %s", pymnt_cycle,
                     pymnt_addr, pymnt_amnt, type)

        if verbose: logger.debug("Reward payment command '{}'".format(cmd))

        client_response = send_request(cmd, verbose)
        response = check_response(client_response)
        hash = get_operation_hash(client_response) if response else ""

        payment_item['paid'] = response
        payment_item['hash'] = hash

        return payment_item

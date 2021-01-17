import argparse
import json
import os
import sys
import traceback
from time import sleep
import ast

import yaml
from fysom import Fysom

from NetworkConfiguration import init_network_config
from api.provider_factory import ProviderFactory
from cli.client_manager import ClientManager
from config.config_parser import ConfigParser
from config.yaml_baking_conf_parser import BakingYamlConfParser
from config.yaml_conf_parser import YamlConfParser
from launch_common import print_banner, add_argument_network, add_argument_reports_base, \
    add_argument_config_dir, add_argument_node_endpoint, add_argument_signer_endpoint, add_argument_docker, \
    add_argument_verbose, add_argument_dry, add_argument_provider, add_argument_api_base_url, add_argument_log_file
from log_config import main_logger, init
from model.baking_conf import BakingConf, BAKING_ADDRESS, PAYMENT_ADDRESS, SERVICE_FEE, FOUNDERS_MAP, OWNERS_MAP, \
    MIN_DELEGATION_AMT, RULES_MAP, MIN_DELEGATION_KEY, DELEGATOR_PAYS_XFER_FEE, DELEGATOR_PAYS_RA_FEE, \
    REACTIVATE_ZEROED, SPECIALS_MAP, SUPPORTERS_SET
from util.address_validator import AddressValidator
from util.dir_utils import get_payment_root, get_successful_payments_dir, get_failed_payments_dir
from util.fee_validator import FeeValidator

LINER = "--------------------------------------------"

logger = main_logger

messages = {
    'hello': 'This application will help you configure TRD to manage payouts for your bakery. Type enter to continue',
    'bakingaddress': 'Specify your baking address public key hash (Processing may take a few seconds)',
    'paymentaddress': 'Specify your payment PKH. Available addresses:{}',
    'servicefee': 'Specify bakery fee [0:100]',
    'foundersmap': "Specify FOUNDERS in form 'PKH1':share1,'PKH2':share2,... (Mind quotes) Type enter to leave empty",
    'ownersmap': "Specify OWNERS in form 'pk1':share1,'pkh2':share2,... (Mind quotes) Type enter to leave empty",
    'mindelegation': "Specify minimum delegation amount in tez. Type enter for 0",
    'mindelegationtarget': "Specify where the reward for delegators failing to satisfy minimum delegation amount go. TOB: leave at balance, TOF: to founders, TOE: to everybody, default is TOB",
    'exclude': "Add excluded address in form of PKH,target. Share of the exluded address will go to target. Possbile targets are= TOB: leave at balance, TOF: to founders, TOE: to everybody. Type enter to skip",
    'redirect': "Add redirected address in form of PKH1,PKH2. Payments for PKH1 will go to PKH2. Type enter to skip",
    'reactivatezeroed': "If a destination address has 0 balance, should burn fee be paid to reactivate? 1 for Yes, 0 for No. Type enter for Yes",
    'delegatorpaysxfrfee': "Who is going to pay for transfer fees: 0 for delegator, 1 for delegate. Type enter for delegator",
    'delegatorpaysrafee': "Who is going to pay for 0 balance reactivation/burn fee: 0 for delegator, 1 for delegate. Type enter for delegator",
    'supporters': "Add supporter address. Supporters do not pay bakery fee. Type enter to skip",
    'specials': "Add any addresses with a special fee in form of 'PKH,fee'. Type enter to skip",
    'final': ""
}

parser = None
wllt_clnt_mngr = None
network_config = None


def printe(msg):
    print(msg, file=sys.stderr, flush=True)


def start():
    fsm.go()


def onbakingaddress(input):
    try:
        AddressValidator("bakingaddress").validate(input)
    except Exception:
        printe("Invalid baking address: " + traceback.format_exc())
        return

    if not input.startswith("tz"):
        printe("Only tz addresses are allowed")
        return
    provider_factory = ProviderFactory(args.reward_data_provider)
    global parser
    parser = BakingYamlConfParser(None, client_manager, provider_factory, network_config, args.node_endpoint,
                                  api_base_url=args.api_base_url)
    parser.set(BAKING_ADDRESS, input)
    fsm.go()


def onpaymentaddress(input):
    try:
        global parser
        parser.set(PAYMENT_ADDRESS, input)
        parser.validate_payment_address(parser.get_conf_obj())
    except Exception:
        printe("Invalid payment address: " + traceback.format_exc())
        return

    fsm.go()


def onservicefee(input):
    try:
        global parser
        parser.set(SERVICE_FEE, float(input))
        parser.validate_service_fee(parser.get_conf_obj())
    except Exception:
        printe("Invalid service fee: " + traceback.format_exc())
        return

    fsm.go()


def onfoundersmap(input):
    try:
        global parser
        dict = ast.literal_eval('{' + input + '}')
        parser.set(FOUNDERS_MAP, dict)
        parser.validate_share_map(parser.get_conf_obj(), FOUNDERS_MAP)
    except Exception:
        printe("Invalid founders input: " + traceback.format_exc())
        return

    fsm.go()


def onownersmap(input):
    try:
        global parser
        dict = ast.literal_eval('{' + input + '}')
        parser.set(OWNERS_MAP, dict)
        parser.validate_share_map(parser.get_conf_obj(), OWNERS_MAP)
    except Exception:
        printe("Invalid owners input: " + traceback.format_exc())
        return

    fsm.go()


def onmindelegation(input):
    try:
        if not input:
            input = "0"
        global parser
        parser.set(MIN_DELEGATION_AMT, float(input))
        parser.validate_service_fee(parser.get_conf_obj())
    except Exception:
        printe("Invalid service fee: " + traceback.format_exc())
        return
    fsm.go()


def onmindelegationtarget(input):
    if not input:
        input = 'TOB'

    try:
        options = ['TOB', 'TOE', 'TOF']
        if input not in options:
            printe("Invalid target, available options are {}".format(options))
            return

        global parser
        conf_obj = parser.get_conf_obj()
        if RULES_MAP not in conf_obj:
            conf_obj[RULES_MAP] = dict()

        conf_obj[RULES_MAP][MIN_DELEGATION_KEY] = input

        parser.validate_dest_map(parser.get_conf_obj())
    except Exception:
        printe("Invalid target: " + traceback.format_exc())
        return
    fsm.go()


def onexclude(input):
    if not input:
        fsm.go()
        return

    try:
        address_target = input.split(',')
        address = address_target[0].strip()
        target = address_target[1].strip()
        AddressValidator("excluded address").validate(address)
        options = ['TOB', 'TOE', 'TOF']
        if target not in options:
            printe("Invalid target, available options are {}".format(options))
            return

        global parser
        conf_obj = parser.get_conf_obj()
        if RULES_MAP not in conf_obj:
            conf_obj[RULES_MAP] = dict()

        conf_obj[RULES_MAP][address] = target

        parser.validate_dest_map(parser.get_conf_obj())
    except Exception:
        printe("Invalid exclusion entry: " + traceback.format_exc())
        return


def onspecials(input):
    if not input:
        fsm.go()
        return

    try:
        address_target = input.split(',')
        address = address_target[0].strip()
        fee = float(address_target[1].strip())
        AddressValidator("special address").validate(address)
        FeeValidator("special_fee").validate(fee)

        global parser
        conf_obj = parser.get_conf_obj()
        if SPECIALS_MAP not in conf_obj:
            conf_obj[SPECIALS_MAP] = dict()

        conf_obj[SPECIALS_MAP][address] = fee

        parser.validate_specials_map(parser.get_conf_obj())
    except Exception:
        printe("Invalid specials entry: " + traceback.format_exc())
        return


def onsupporters(input):
    if not input:
        fsm.go()
        return

    try:
        AddressValidator("supporter address").validate(input)

        global parser
        conf_obj = parser.get_conf_obj()
        if SUPPORTERS_SET not in conf_obj:
            conf_obj[SUPPORTERS_SET] = set()

        conf_obj[SUPPORTERS_SET].add(input)

        parser.validate_address_set(parser.get_conf_obj(), SUPPORTERS_SET)
    except Exception:
        printe("Invalid supporter entry: " + traceback.format_exc())
        return


def onredirect(input):
    if not input:
        fsm.go()
        return

    try:
        address1_address2 = input.split(',')
        address1 = address1_address2[0].strip()
        address2 = address1_address2[1].strip()

        AddressValidator("redirected source address").validate(address1)
        AddressValidator("redirected target address").validate(address2)

        global parser
        conf_obj = parser.get_conf_obj()
        if RULES_MAP not in conf_obj:
            conf_obj[RULES_MAP] = dict()

        conf_obj[RULES_MAP][address1] = address2

        parser.validate_dest_map(parser.get_conf_obj())
    except Exception:
        printe("Invalid redirection entry: " + traceback.format_exc())
        return


def ondelegatorpaysxfrfee(input):
    try:
        if not input:
            input = "0"
        if input != "0" and input != "1":
            raise Exception("Please enter '0' or '1'")
        global parser
        parser.set(DELEGATOR_PAYS_XFER_FEE, input != "1")
    except Exception as e:
        printe("Invalid input: {}".format(str(e)))
        return
    fsm.go()


def ondelegatorpaysrafee(input):
    try:
        if not input:
            input = "0"
        if input != "0" and input != "1":
            raise Exception("Please enter '0' or '1'")
        global parser
        parser.set(DELEGATOR_PAYS_RA_FEE, input != "1")
    except Exception as e:
        printe("Invalid input: {}".format(str(e)))
        return
    fsm.go()


def onreactivatezeroed(input):
    try:
        if not input:
            input = "0"
        if input != "0" and input != "1":
            raise Exception("Please enter '0' or '1'")
        global parser
        parser.set(REACTIVATE_ZEROED, input != "1")
    except Exception as e:
        printe("Invalid input: {}".format(str(e)))
        return
    fsm.go()


def onfinal(input):
    pass


callbacks = {
    'bakingaddress': onbakingaddress,
    'paymentaddress': onpaymentaddress,
    'servicefee': onservicefee,
    'foundersmap': onfoundersmap,
    'ownersmap': onownersmap,
    'mindelegation': onmindelegation,
    'mindelegationtarget': onmindelegationtarget,
    'exclude': onexclude,
    'redirect': onredirect,
    'reactivatezeroed': onreactivatezeroed,
    'delegatorpaysxfrfee': ondelegatorpaysxfrfee,
    'delegatorpaysrafee': ondelegatorpaysrafee,
    'supporters': onsupporters,
    'specials': onspecials,
    'final': onfinal
}

fsm = Fysom({'initial': 'hello', 'final': 'final',
             'events': [
                 {'name': 'go', 'src': 'hello', 'dst': 'bakingaddress'},
                 {'name': 'go', 'src': 'bakingaddress', 'dst': 'paymentaddress'},
                 {'name': 'go', 'src': 'paymentaddress', 'dst': 'servicefee'},
                 {'name': 'go', 'src': 'servicefee', 'dst': 'foundersmap'},
                 {'name': 'go', 'src': 'foundersmap', 'dst': 'ownersmap'},
                 {'name': 'go', 'src': 'ownersmap', 'dst': 'mindelegation'},
                 {'name': 'go', 'src': 'mindelegation', 'dst': 'mindelegationtarget'},
                 {'name': 'go', 'src': 'mindelegationtarget', 'dst': 'exclude'},
                 {'name': 'go', 'src': 'exclude', 'dst': 'redirect'},
                 {'name': 'go', 'src': 'redirect', 'dst': 'reactivatezeroed'},
                 {'name': 'go', 'src': 'reactivatezeroed', 'dst': 'delegatorpaysrafee'},
                 {'name': 'go', 'src': 'delegatorpaysrafee', 'dst': 'delegatorpaysxfrfee'},
                 {'name': 'go', 'src': 'delegatorpaysxfrfee', 'dst': 'specials'},
                 {'name': 'go', 'src': 'specials', 'dst': 'supporters'},
                 {'name': 'go', 'src': 'supporters', 'dst': 'final'}],
             'callbacks': {
                 'bakingaddress': onbakingaddress}
             })


def main(args):
    logger.info("Arguments Configuration = {}".format(json.dumps(args.__dict__, indent=1)))

    # 1- find where configuration is
    config_dir = os.path.expanduser(args.config_dir)

    # create configuration directory if it is not present
    # so that user can easily put his configuration there
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # 2- Load master configuration file if it is present
    master_config_file_path = os.path.join(config_dir, "master.yaml")

    master_cfg = {}
    if os.path.isfile(master_config_file_path):
        logger.debug("Loading master configuration file {}".format(master_config_file_path))

        master_parser = YamlConfParser(ConfigParser.load_file(master_config_file_path))
        master_cfg = master_parser.parse()
    else:
        logger.debug("master configuration file not present.")

    managers = None
    contracts_by_alias = None
    addresses_by_pkh = None
    if 'managers' in master_cfg:
        managers = master_cfg['managers']
    if 'contracts_by_alias' in master_cfg:
        contracts_by_alias = master_cfg['contracts_by_alias']
    if 'addresses_by_pkh' in master_cfg:
        addresses_by_pkh = master_cfg['addresses_by_pkh']

    # 4. get network config
    global client_manager
    client_manager = ClientManager(node_endpoint = args.node_endpoint,
                                   signer_endpoint = args.signer_endpoint)

    network_config_map = init_network_config(args.network, client_manager)
    global network_config
    network_config = network_config_map[args.network]
    logger.debug("Network config {}".format(network_config))


    # hello state
    input("{} >".format(messages['hello'])).strip()
    start()

    while not fsm.is_finished():
        sleep(0.1)
        command = input("{} >\n".format(messages[fsm.current])).strip()
        callbacks[fsm.current](command)
    pass

    parser.validate()
    parser.process()
    cfg_dict = parser.get_conf_obj()

    # dictionary to BakingConf object, for a bit of type safety
    cfg = BakingConf(cfg_dict, master_cfg)

    config_file_path = os.path.join(os.path.abspath(config_dir), cfg.get_baking_address() + '.yaml')
    cfg_dict_plain = {k: v for k, v in cfg_dict.items() if not k.startswith('__')}
    with open(config_file_path, 'w') as outfile:
        yaml.dump(cfg_dict_plain, outfile, default_flow_style=True, indent=4)

        print("Configuration file is created at '{}'".format(config_file_path))


def load_config_file(wllt_clnt_mngr, network_config, master_cfg):
    provider_factory = ProviderFactory(args.reward_data_provider)
    parser = BakingYamlConfParser(None, wllt_clnt_mngr, provider_factory, network_config, args.node_addr,
                                  api_base_url=args.api_base_url)
    parser.parse()
    parser.validate()
    parser.process()
    cfg_dict = parser.get_conf_obj()

    # dictionary to BakingConf object, for a bit of type safety
    cfg = BakingConf(cfg_dict, master_cfg)

    logger.info("Baking Configuration {}".format(cfg))

    baking_address = cfg.get_baking_address()
    payment_address = cfg.get_payment_address()
    logger.info(LINER)
    logger.info("BAKING ADDRESS is {}".format(baking_address))
    logger.info("PAYMENT ADDRESS is {}".format(payment_address))
    logger.info(LINER)

    # 7- get reporting directories
    reports_dir = os.path.expanduser(args.reports_base)

    reports_dir = os.path.join(reports_dir, baking_address)

    payments_root = get_payment_root(reports_dir, create=True)
    get_successful_payments_dir(payments_root, create=True)
    get_failed_payments_dir(payments_root, create=True)


def get_baking_configuration_file(config_dir):
    config_file = None
    for file in os.listdir(config_dir):
        if file.endswith(".yaml") and not file.startswith("master"):
            if config_file:
                raise Exception(
                    "Application only supports one baking configuration file. Found at least 2 {}, {}".format(
                        config_file, file))
            config_file = file
    if config_file is None:
        raise Exception(
            "Unable to find any '.yaml' configuration files inside configuration directory({})".format(config_dir))

    return os.path.join(config_dir, config_file)


def get_latest_report_file(payments_root):
    recent = None
    if get_successful_payments_dir(payments_root):
        files = sorted([os.path.splitext(x)[0] for x in os.listdir(get_successful_payments_dir(payments_root))],
                       key=lambda x: int(x))
        recent = files[-1] if len(files) > 0 else None
    return recent


class ReleaseOverrideAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not -11 <= values:
            parser.error("Valid range for release-override({0}) is [-11,) ".format(option_string))

        setattr(namespace, "release_override", values)


if __name__ == '__main__':

    if not sys.version_info.major >= 3 and sys.version_info.minor >= 6:
        raise Exception(
            "Must be using Python 3.6 or later but it is {}.{}".format(sys.version_info.major, sys.version_info.minor))

    parser = argparse.ArgumentParser()

    add_argument_provider(parser)
    add_argument_network(parser)
    add_argument_reports_base(parser)
    add_argument_config_dir(parser)
    add_argument_node_endpoint(parser)
    add_argument_signer_endpoint(parser)
    add_argument_docker(parser)
    add_argument_verbose(parser)
    add_argument_dry(parser)
    add_argument_api_base_url(parser)
    add_argument_log_file(parser)

    args = parser.parse_args()

    init(False, args.log_file, args.verbose == 'on', mode='configure')

    script_name = " Baker Configuration Tool"
    args.dry_run = False
    print_banner(args, script_name)

    main(args)

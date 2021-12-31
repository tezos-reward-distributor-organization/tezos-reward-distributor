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
from Constants import RewardsType
from config.yaml_baking_conf_parser import BakingYamlConfParser
from launch_common import (
    print_banner,
    add_argument_network,
    add_argument_reports_base,
    add_argument_config_dir,
    add_argument_node_endpoint,
    add_argument_signer_endpoint,
    add_argument_docker,
    add_argument_verbose,
    add_argument_dry,
    add_argument_provider,
    add_argument_api_base_url,
    add_argument_log_file,
)
from log_config import main_logger, init
from model.baking_conf import (
    BakingConf,
    BAKING_ADDRESS,
    PAYMENT_ADDRESS,
    SERVICE_FEE,
    FOUNDERS_MAP,
    OWNERS_MAP,
    MIN_DELEGATION_AMT,
    RULES_MAP,
    MIN_DELEGATION_KEY,
    DELEGATOR_PAYS_XFER_FEE,
    DELEGATOR_PAYS_RA_FEE,
    REACTIVATE_ZEROED,
    SPECIALS_MAP,
    SUPPORTERS_SET,
    REWARDS_TYPE,
    PAY_DENUNCIATION_REWARDS,
)
from util.address_validator import AddressValidator
from util.fee_validator import FeeValidator

LINER = "--------------------------------------------"

logger = main_logger

messages = {
    "hello": "This application will help you configure TRD to manage payouts for your bakery. Type enter to continue",
    "bakingaddress": "Specify your baking address public key hash (Processing may take a few seconds)",
    "paymentaddress": "Specify your payouts public key hash. It can be the same as your baking address, or a different one.",
    "servicefee": "Specify bakery fee [0:100]",
    "rewardstype": "Specify if baker pays 'ideal' or 'actual' rewards (Be sure to read the documentation to understand the difference). Type enter for 'actual'",
    "foundersmap": "Specify FOUNDERS in form 'PKH1':share1,'PKH2':share2,... (Mind quotes) Type enter to leave empty",
    "ownersmap": "Specify OWNERS in form 'pk1':share1,'pkh2':share2,... (Mind quotes) Type enter to leave empty",
    "mindelegation": "Specify minimum delegation amount in tez. Type enter for 0",
    "mindelegationtarget": "Specify where the reward for delegators failing to satisfy minimum delegation amount go. TOB: leave at balance, TOF: to founders, TOE: to everybody, default is TOB",
    "exclude": "Add excluded address in form of PKH,target. Share of the exluded address will go to target. Possbile targets are= TOB: leave at balance, TOF: to founders, TOE: to everybody. Type enter to skip",
    "redirect": "Add redirected address in form of PKH1,PKH2. Payments for PKH1 will go to PKH2. Type enter to skip",
    "reactivatezeroed": "If a destination address has 0 balance, should burn fee be paid to reactivate? 1 for Yes, 0 for No. Type enter for Yes",
    "delegatorpaysxfrfee": "Who is going to pay for transfer fees: 0 for delegator, 1 for delegate. Type enter for delegator",
    "delegatorpaysrafee": "Who is going to pay for 0 balance reactivation/burn fee: 0 for delegator, 1 for delegate. Type enter for delegator",
    "paydenunciationrewards": "If you denounce another baker for baking or endorsing, you will get rewarded. Distribute denunciation rewards to your delegators? 1 for Yes, 0 for No. Type enter for No",
    "supporters": "Add supporter address. Supporters do not pay bakery fee. Type enter to skip",
    "specials": "Add any addresses with a special fee in form of 'PKH,fee'. Type enter to skip",
    "noplugins": "No plugins are enabled by default. If you wish to use the email, twitter, or telegram plugins, please read the documentation and edit the configuration file manually.",
}

parser = None
clnt_mngr = None
network_config = None


def printe(msg):
    print(msg, file=sys.stderr, flush=True)


def start():
    fsm.go()


def onbakingaddress(input):
    try:
        AddressValidator("baking address").validate(input)
    except Exception as e:
        printe(f"Invalid baking address: {str(e)}")
        return

    if not input.startswith("tz"):
        printe("Only tz addresses are allowed")
        return
    provider_factory = ProviderFactory(args.reward_data_provider)
    global parser
    parser = BakingYamlConfParser(
        None,
        client_manager,
        provider_factory,
        network_config,
        args.node_endpoint,
        api_base_url=args.api_base_url,
    )
    parser.set(BAKING_ADDRESS, input)
    fsm.go()


def onpaymentaddress(input):
    try:

        AddressValidator("payouts address").validate(input)

        global parser
        parser.set(PAYMENT_ADDRESS, input)
        parser.validate_payment_address(parser.get_conf_obj())
    except Exception as e:
        printe(f"Invalid payouts address: {str(e)}")
        return

    fsm.go()


def onservicefee(input):
    try:
        global parser
        parser.set(SERVICE_FEE, float(input))
        parser.validate_service_fee(parser.get_conf_obj())
    except Exception as e:
        printe(
            f"Invalid service fee: {str(e)}\nPlease enter a value between 0 and 100."
        )
        return

    fsm.go()


def onrewardstype(input):
    if not input:
        input = "actual"

    try:
        global parser
        rt = RewardsType(input.lower())
        parser.set(REWARDS_TYPE, str(rt))
    except Exception:
        printe("Invalid option for rewards type. Please enter 'actual' or 'ideal'.")
        return

    fsm.go()


def onfoundersmap(input):
    try:
        global parser
        dict = ast.literal_eval("{" + input + "}")
        parser.set(FOUNDERS_MAP, dict)
        parser.validate_share_map(parser.get_conf_obj(), FOUNDERS_MAP)
    except Exception:
        printe("Invalid founders input: " + traceback.format_exc())
        return

    fsm.go()


def onownersmap(input):
    try:
        global parser
        dict = ast.literal_eval("{" + input + "}")
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
        input = "TOB"

    try:
        options = ["TOB", "TOE", "TOF"]
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
        address_target = input.split(",")
        address = address_target[0].strip()
        target = address_target[1].strip()
        AddressValidator("excluded address").validate(address)
        options = ["TOB", "TOE", "TOF"]
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
        address_target = input.split(",")
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
        address1_address2 = input.split(",")
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


def onpaydenunciationrewards(input):
    try:
        if not input:
            input = "1"
        if input != "0" and input != "1":
            raise Exception("Please enter '0' or '1'")
        global parser
        parser.set(PAY_DENUNCIATION_REWARDS, input != "1")
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


def onprefinal(input):
    fsm.go()


callbacks = {
    "bakingaddress": onbakingaddress,
    "paymentaddress": onpaymentaddress,
    "servicefee": onservicefee,
    "rewardstype": onrewardstype,
    "foundersmap": onfoundersmap,
    "ownersmap": onownersmap,
    "mindelegation": onmindelegation,
    "mindelegationtarget": onmindelegationtarget,
    "exclude": onexclude,
    "redirect": onredirect,
    "reactivatezeroed": onreactivatezeroed,
    "delegatorpaysxfrfee": ondelegatorpaysxfrfee,
    "delegatorpaysrafee": ondelegatorpaysrafee,
    "paydenunciationrewards": onpaydenunciationrewards,
    "supporters": onsupporters,
    "specials": onspecials,
    "prefinal": onprefinal,
}

fsm = Fysom(
    {
        "initial": "hello",
        "final": "final",
        "events": [
            {"name": "go", "src": "hello", "dst": "bakingaddress"},
            {"name": "go", "src": "bakingaddress", "dst": "paymentaddress"},
            {"name": "go", "src": "paymentaddress", "dst": "servicefee"},
            {"name": "go", "src": "servicefee", "dst": "rewardstype"},
            {"name": "go", "src": "rewardstype", "dst": "foundersmap"},
            {"name": "go", "src": "foundersmap", "dst": "ownersmap"},
            {"name": "go", "src": "ownersmap", "dst": "mindelegation"},
            {"name": "go", "src": "mindelegation", "dst": "mindelegationtarget"},
            {"name": "go", "src": "mindelegationtarget", "dst": "exclude"},
            {"name": "go", "src": "exclude", "dst": "redirect"},
            {"name": "go", "src": "redirect", "dst": "reactivatezeroed"},
            {"name": "go", "src": "reactivatezeroed", "dst": "delegatorpaysrafee"},
            {"name": "go", "src": "delegatorpaysrafee", "dst": "delegatorpaysxfrfee"},
            {
                "name": "go",
                "src": "delegatorpaysxfrfee",
                "dst": "paydenunciationrewards",
            },
            {"name": "go", "src": "paydenunciationrewards", "dst": "specials"},
            {"name": "go", "src": "specials", "dst": "supporters"},
            {"name": "go", "src": "supporters", "dst": "final"},
        ],
        "callbacks": {"bakingaddress": onbakingaddress},
    }
)


def main(args):
    logger.info(
        "Arguments Configuration = {}".format(json.dumps(args.__dict__, indent=1))
    )

    # 1. find where configuration is
    config_dir = os.path.expanduser(args.config_dir)

    # create configuration directory if it is not present
    # so that user can easily put his configuration there
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # 2. get network config
    global client_manager
    client_manager = ClientManager(
        node_endpoint=args.node_endpoint, signer_endpoint=args.signer_endpoint
    )

    network_config_map = init_network_config(args.network, client_manager)
    global network_config
    network_config = network_config_map[args.network]
    logger.debug("Network config {}".format(network_config))

    # hello state
    input("{} >".format(messages["hello"])).strip()
    start()

    # 3. loop while collecting information
    while not fsm.is_finished():
        sleep(0.1)
        command = input("{} >\n".format(messages[fsm.current])).strip()
        callbacks[fsm.current](command)

    # 4. parse and process config
    parser.validate()
    parser.process()
    cfg_dict = parser.get_conf_obj()

    # dictionary to BakingConf object, for a bit of type safety
    cfg = BakingConf(cfg_dict)

    config_file_path = os.path.join(
        os.path.abspath(config_dir), cfg.get_baking_address() + ".yaml"
    )
    cfg_dict_plain = {k: v for k, v in cfg_dict.items() if not k.startswith("__")}

    try:
        with open(config_file_path, "w") as outfile:
            yaml.dump(cfg_dict_plain, outfile, default_flow_style=False, indent=4)
    except Exception as e:
        import errno

        print("Exception during write operation invoked: {}".format(e))
        if e.errno == errno.ENOSPC:
            print("Not enough space on device!")
        exit()

    print(messages["noplugins"])
    print("Configuration file is created at '{}'".format(config_file_path))


class ReleaseOverrideAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values < -11 or values > 0:
            parser.error(
                "release-override({0}) must be in the range of [-11,-1] to override, default is 0".format(
                    option_string
                )
            )

        setattr(namespace, "release_override", values)


if __name__ == "__main__":

    if not sys.version_info.major >= 3 and sys.version_info.minor >= 6:
        raise Exception(
            "Must be using Python 3.6 or later but it is {}.{}".format(
                sys.version_info.major, sys.version_info.minor
            )
        )

    argparser = argparse.ArgumentParser()

    add_argument_provider(argparser)
    add_argument_network(argparser)
    add_argument_reports_base(argparser)
    add_argument_config_dir(argparser)
    add_argument_node_endpoint(argparser)
    add_argument_signer_endpoint(argparser)
    add_argument_docker(argparser)
    add_argument_verbose(argparser)
    add_argument_dry(argparser)
    add_argument_api_base_url(argparser)
    add_argument_log_file(argparser)

    args = argparser.parse_args()

    init(False, args.log_file, args.verbose == "on", mode="configure")

    script_name = " Baker Configuration Tool"
    args.dry_run = False
    print_banner(args, script_name)

    main(args)

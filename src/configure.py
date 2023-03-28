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
from Constants import RewardsType, CONFIG_DIR, PYTHON_MAJOR, PYTHON_MINOR, LINER
from config.yaml_baking_conf_parser import BakingYamlConfParser
from launch_common import print_banner
from util.parser import (
    add_argument_network,
    add_argument_base_directory,
    add_argument_node_endpoint,
    add_argument_signer_endpoint,
    add_argument_verbose,
    add_argument_provider,
    add_argument_api_base_url,
    add_argument_log_file,
)
from util.args_validator import validate
from log_config import main_logger, init
from model.baking_conf import (
    BakingConf,
    BAKING_ADDRESS,
    PAYMENT_ADDRESS,
    SERVICE_FEE,
    FOUNDERS_MAP,
    OWNERS_MAP,
    MIN_DELEGATION_AMT,
    MIN_PAYMENT_AMT,
    RULES_MAP,
    MIN_DELEGATION_KEY,
    DELEGATOR_PAYS_XFER_FEE,
    DELEGATOR_PAYS_RA_FEE,
    REACTIVATE_ZEROED,
    SPECIALS_MAP,
    SUPPORTERS_SET,
    REWARDS_TYPE,
    PAY_DENUNCIATION_REWARDS,
    TOB,
    TOE,
    TOF,
)
from util.address_validator import AddressValidator
from util.fee_validator import FeeValidator
from util.exit_program import exit_program, ExitCode


logger = main_logger

messages = {
    "hello": "This application will help you configure TRD to manage payouts for your bakery. Press enter to continue",
    "bakingaddress": "Specify your baking address public key hash (Processing may take a few seconds)",
    "paymentaddress": "Specify your payouts public key hash. It can be the same as your baking address, or a different one.",
    "servicefee": "Specify bakery fee, valid range is between 0 and 100",
    "rewardstype": "Specify if baker pays 'ideal' or 'actual' rewards (Be sure to read the documentation to understand the difference). Press enter for 'actual'",
    "foundersmap": "Specify FOUNDERS in form 'tz-address':share1,'tz-address':share2,... (Mind quotes, sum must equal 1, e.g: 'tz1a...':0.3, 'tz1b..':0.7) Press enter to leave empty",
    "ownersmap": "Specify OWNERS in form 'tz-address':share1,'tz-address':share2,... (Mind quotes, sum must equal 1, e.g: 'tz1a...':0.3, 'tz1b..':0.7) Press enter to leave empty",
    "mindelegation": "Specify minimum delegation amount in tez. Press enter for 0",
    "mindelegationtarget": "Specify where the reward for delegators failing to satisfy minimum delegation amount go. {}: leave at balance, {}: to founders, {}: to everybody, press enter for {}".format(
        TOB, TOF, TOE, TOB
    ),
    "exclude": "Add excluded address in form of 'tz-address1':'target', 'tz-address2':'target'. (e.g: 'tz1a..:'TOF','tz1b..:'TOB') Share of the exluded address will go to target. Possbile targets are = {}: leave at balance, {}: to founders, {}: to everybody. Type enter to skip".format(
        TOB, TOF, TOE
    ),
    "redirect": "Add redirected address in form of 'tz-address1':'tz-address2', 'tz-address3':'tz-address4'. (e.g: 'tz1a..:'tz1b..','tz1c..:'tz1d..'). Press enter to skip",
    "reactivatezeroed": "If a destination address has 0 balance, should burn fee be paid to reactivate? 1 for Yes, 0 for No. Press enter for Yes",
    "delegatorpaysxfrfee": "Who is going to pay for transfer fees: 0 for delegator, 1 for delegate. Press enter for delegator",
    "delegatorpaysrafee": "Who is going to pay for 0 balance reactivation or burn fees for kt accounts in general: 0 for delegator, 1 for delegate. Press enter for delegator",
    "paydenunciationrewards": "If you denounce another baker for baking or endorsing, you will get rewarded. Distribute denunciation rewards to your delegators? 1 for Yes, 0 for No. Press enter for No",
    "supporters": "Add supporter addresses in form of 'tz-address1', 'tz-address2'. Supporters do not pay bakery fee. Press enter to skip",
    "specials": "Add any addresses with a special fee in form of 'tz-address1':fee, 'tz-address2':fee. Press enter to skip",
    "noplugins": "No plugins are enabled by default. If you wish to use the email, twitter, or telegram plugins, please read the documentation and edit the configuration file manually.",
    "minpayment": "Specify minimum payment amount in tez. Press enter for 0",
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
        AddressValidator().validate(input)
        global parser
        parser = BakingYamlConfParser(
            None,
            client_manager,
            ProviderFactory(args.reward_data_provider),
            network_config,
            args.node_endpoint,
            api_base_url=args.api_base_url,
        )
        parser.set(BAKING_ADDRESS, input)
        parser.validate_baking_address(parser.get_conf_obj())
        fsm.go()
    except Exception as e:
        printe(f"Invalid baking address: {str(e)}")
        return


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
        input = RewardsType.ACTUAL.value
    try:
        global parser
        rt = RewardsType(input.lower())
        parser.set(REWARDS_TYPE, str(rt))
    except Exception:
        printe("Invalid option for rewards type. Please type 'actual' or 'ideal'.")
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
        parser.validate_min_delegation_amt(parser.get_conf_obj())
    except Exception:
        printe("Invalid minimum delegation amount: " + traceback.format_exc())
        return
    fsm.go()


def onminpayment(input):
    try:
        if not input:
            input = "0"
        global parser
        parser.set(MIN_PAYMENT_AMT, float(input))
        parser.validate_min_payment_amt(parser.get_conf_obj())
    except Exception:
        printe("Invalid minimum payment amount: " + traceback.format_exc())
        return
    fsm.go()


def onmindelegationtarget(input):
    if not input:
        input = TOB

    try:
        options = [TOB, TOE, TOF]
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
        global parser

        dict = ast.literal_eval("{" + input + "}")
        parser.set(RULES_MAP, dict)
        parser.validate_excluded_map(parser.get_conf_obj(), RULES_MAP)

    except Exception:
        printe("Invalid exclusion entry: " + traceback.format_exc())
        return
    fsm.go()


def onspecials(input):
    if not input:
        fsm.go()
        return

    try:
        global parser
        dict = ast.literal_eval("{" + input + "}")
        parser.set(SPECIALS_MAP, dict)

        parser.validate_specials_map(parser.get_conf_obj())
    except Exception:
        printe("Invalid specials entry: " + traceback.format_exc())
        return
    fsm.go()


def onsupporters(input):
    if not input:
        fsm.go()
        return

    try:
        global parser
        dict = ast.literal_eval("{" + input + "}")
        parser.set(SUPPORTERS_SET, dict)
        parser.validate_address_set(parser.get_conf_obj(), SUPPORTERS_SET)

    except Exception:
        printe("Invalid supporter entry: " + traceback.format_exc())
        return
    fsm.go()


def onredirect(input):
    if not input:
        fsm.go()
        return

    try:
        global parser

        dict = ast.literal_eval("{" + input + "}")
        parser.set(RULES_MAP, dict)
        parser.validate_dest_map(parser.get_conf_obj())

    except Exception:
        printe("Invalid redirection entry: " + traceback.format_exc())
        return
    fsm.go()


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
    "minpayment": onminpayment,
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
            {"name": "go", "src": "mindelegationtarget", "dst": "minpayment"},
            {"name": "go", "src": "minpayment", "dst": "exclude"},
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
    config_dir = os.path.join(
        os.path.expanduser(os.path.normpath(args.base_directory)), CONFIG_DIR, ""
    )

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

    if os.path.exists:
        while True:
            try:
                print(
                    "Configuration file already exists, would you like to overwrite it or choose a new file name? type either overwrite or new."
                )
                user_input = input()
                if user_input != "overwrite" and user_input != "new":
                    raise Exception("Please enter 'overwrite' or 'new'")
                if user_input == "new":
                    print(
                        "please enter new filename without extention, e.g: updated-configuration"
                    )
                    config_file_path = os.path.join(
                        os.path.abspath(config_dir), input() + ".yaml"
                    )
                    break
                if user_input == "overwrite":
                    break
            except Exception as e:
                printe("Invalid input: {}".format(str(e)))

    cfg_dict_plain = {k: v for k, v in cfg_dict.items() if not k.startswith("__")}

    try:
        with open(config_file_path, "w") as outfile:
            yaml.dump(cfg_dict_plain, outfile, default_flow_style=False, indent=4)
    except Exception as e:
        import errno

        if e.errno == errno.ENOSPC:
            error_msg = "Exception during write operation invoked: {}. Not enough space on device.".format(
                e
            )
        else:
            error_msg = "Exception during write operation invoked: {}".format(e)
        exit_program(ExitCode.GENERAL_ERROR, error_msg)

    print(messages["noplugins"])
    print("Configuration file is created at '{}'".format(config_file_path))


if __name__ == "__main__":

    if not (
        sys.version_info.major >= PYTHON_MAJOR
        and sys.version_info.minor >= PYTHON_MINOR
    ):
        raise Exception(
            "Must be using Python {}.{} or later but it is {}.{}".format(
                PYTHON_MAJOR,
                PYTHON_MINOR,
                sys.version_info.major,
                sys.version_info.minor,
            )
        )

    argparser = argparse.ArgumentParser()
    add_argument_provider(argparser)
    add_argument_network(argparser)
    add_argument_base_directory(argparser)
    add_argument_node_endpoint(argparser)
    add_argument_signer_endpoint(argparser)
    add_argument_verbose(argparser)
    add_argument_api_base_url(argparser)
    add_argument_log_file(argparser)

    # Basic validations
    # You only have access to the parsed values after you parse_args()
    args = validate(argparser)

    init(False, args.log_file, args.verbose == "on", mode="configure")

    script_name = " Baker Configuration Tool"
    print_banner(args, script_name)

    main(args)

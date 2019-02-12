import argparse
import json
import os
import shutil
import sys

import yaml

from BusinessConfiguration import BAKING_ADDRESS, STANDARD_FEE, founders_map, owners_map, specials_map, supporters_set, \
    MIN_DELEGATION_AMT
from BusinessConfigurationX import prcnt_scale, pymnt_scale, excluded_delegators_set
from log_config import main_logger
from util.dir_utils import get_payment_root, \
    get_calculations_root, get_successful_payments_dir, get_failed_payments_dir

LINER = "--------------------------------------------"

logger = main_logger


def main(args):
    logger.info("Arguments Configuration = {}".format(json.dumps(args.__dict__, indent=1)))

    # find where configuration is
    config_dir = os.path.expanduser(args.config_dir)

    # create configuration directory if it is not present
    # so that user can easily put his configuration there
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # load baking configuration file
    config_file_path = os.path.join(config_dir, BAKING_ADDRESS + ".yaml")

    logger.info("Creating baking configuration file {}".format(config_file_path))

    bkg_cfg_dict = {}
    bkg_cfg_dict['version'] = '1.0'
    bkg_cfg_dict['baking_address'] = BAKING_ADDRESS
    bkg_cfg_dict['payment_address'] = args.paymentaddress
    bkg_cfg_dict['service_fee'] = STANDARD_FEE * 100
    bkg_cfg_dict['founders_map'] = founders_map
    bkg_cfg_dict['owners_map'] = owners_map
    bkg_cfg_dict['prcnt_scale'] = prcnt_scale
    bkg_cfg_dict['pymnt_scale'] = pymnt_scale
    for key, value in specials_map.items():
        specials_map[key] = value * 100
    bkg_cfg_dict['specials_map'] = specials_map
    bkg_cfg_dict['supporters_set'] = supporters_set
    bkg_cfg_dict['min_delegation_amt'] = MIN_DELEGATION_AMT
    bkg_cfg_dict['excluded_delegators_set'] = excluded_delegators_set

    if args.verbose:
        dump = yaml.dump(bkg_cfg_dict, default_flow_style=False)
        logger.info("Generated yaml configuration {}".format(dump))

    with open(config_file_path, 'w') as outfile:
        yaml.dump(bkg_cfg_dict, outfile, default_flow_style=False)

    legacy_reports_dir = os.path.expanduser(args.legacy_reports_dir)
    legacy_payments_root = get_payment_root(legacy_reports_dir, create=False)
    legacy_successful_payments_dir = get_successful_payments_dir(legacy_payments_root, create=False)
    legacy_failed_payments_dir = get_failed_payments_dir(legacy_payments_root, create=False)
    legacy_calculations_root = get_calculations_root(legacy_reports_dir, create=False)

    # 7- get reporting directories
    reports_dir = os.path.expanduser(args.reports_dir)
    reports_dir = os.path.join(reports_dir, BAKING_ADDRESS)
    payments_root = get_payment_root(reports_dir, create=True)
    calculations_root = get_calculations_root(reports_dir, create=True)
    successful_payments_dir = get_successful_payments_dir(payments_root, create=True)
    failed_payments_dir = get_failed_payments_dir(payments_root, create=True)

    logger.info("Copy success logs")
    copy_files(legacy_successful_payments_dir, successful_payments_dir, args.verbose)
    logger.info("Copy fail logs")
    copy_files(legacy_failed_payments_dir, failed_payments_dir, args.verbose)
    logger.info("Copy calculation logs")
    copy_files(legacy_calculations_root, calculations_root, args.verbose)


def copy_files(src, dest, verbose):
    src_files = os.listdir(src)
    for file_name in src_files:
        full_file_name = os.path.join(src, file_name)
        if (os.path.isfile(full_file_name)):
            shutil.copy(full_file_name, dest)
            if verbose:
                logger.info("Copied file from {} to {}".format(full_file_name,dest))


if __name__ == '__main__':

    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3")

    parser = argparse.ArgumentParser()
    parser.add_argument("paymentaddress",
                        help="tezos account address (PKH) or an alias to make payments. If tezos signer is used "
                             "to sign for the address, it is necessary to use an alias.")
    parser.add_argument("-rl", "--legacy_reports_dir", help="Directory used to create reports before migration",
                        default='./reports')
    parser.add_argument("-r", "--reports_dir", help="Directory to create reports", default='~/pymnt/reports')
    parser.add_argument("-f", "--config_dir", help="Directory to find baking configurations", default='~/pymnt/cfg')
    parser.add_argument("-V", "--verbose",
                        help="Low level details.",
                        action="store_true", default=True)
    args = parser.parse_args()

    logger.info("Tezos Reward Distributor Migration Tool V2->V3 is Starting")
    logger.info(LINER)
    logger.info("Copyright Hüseyin ABANOZ 2019")
    logger.info("huseyinabanox@gmail.com")
    logger.info("Please leave copyright information")
    logger.info(LINER)
    main(args)

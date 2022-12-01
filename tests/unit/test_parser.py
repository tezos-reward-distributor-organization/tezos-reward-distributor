import argparse
import pytest
from util.parser import (
    build_parser,
    add_argument_verbose,
    add_argument_log_file,
    add_argument_syslog,
    add_argument_retry_injected,
    add_argument_api_base_url,
    add_argument_cycle,
    add_argument_stats,
    add_argument_docker,
    add_argument_signer_endpoint,
    add_argument_dry,
    add_argument_mode,
    add_argument_base_directory,
    add_argument_node_addr_public,
    add_argument_release_override,
    add_argument_payment_offset,
    add_argument_network,
    add_argument_node_endpoint,
    add_argument_provider,
)


@pytest.mark.parametrize(
    "argument, expected",
    [
        (add_argument_cycle, argparse.Namespace(initial_cycle=-1)),
        (add_argument_mode, argparse.Namespace(run_mode=1)),
        (add_argument_release_override, argparse.Namespace(release_override=0)),
        (add_argument_payment_offset, argparse.Namespace(payment_offset=0)),
        (add_argument_network, argparse.Namespace(network="MAINNET")),
        (
            add_argument_node_endpoint,
            argparse.Namespace(node_endpoint="http://127.0.0.1:8732"),
        ),
        (add_argument_provider, argparse.Namespace(reward_data_provider="tzkt")),
        (
            add_argument_node_addr_public,
            argparse.Namespace(node_addr_public="https://rpc.tzkt.io/mainnet"),
        ),
        (add_argument_base_directory, argparse.Namespace(base_directory="~/pymnt")),
        (add_argument_dry, argparse.Namespace(dry_run='signer')),
        (
            add_argument_signer_endpoint,
            argparse.Namespace(signer_endpoint="http://127.0.0.1:6732"),
        ),
        (add_argument_docker, argparse.Namespace(docker=False)),
        (add_argument_stats, argparse.Namespace(do_not_publish_stats=False)),
        (add_argument_verbose, argparse.Namespace(verbose="on")),
        (add_argument_api_base_url, argparse.Namespace(api_base_url=None)),
        (add_argument_retry_injected, argparse.Namespace(retry_injected=False)),
        (add_argument_syslog, argparse.Namespace(syslog=False)),
        (add_argument_log_file, argparse.Namespace(log_file="~/pymnt/logs/app.log")),
    ],
)
def test_add_argument_to_argparser_with_default(argument, expected):
    argparser = argparse.ArgumentParser(prog="TRD")
    argument(argparser)
    args, unknown = argparser.parse_known_args()
    assert args == expected


def test_build_parser():
    value = build_parser()
    assert value.parse_known_args()[0] == argparse.Namespace(
        initial_cycle=-1,
        run_mode=1,
        release_override=0,
        payment_offset=0,
        network="MAINNET",
        node_endpoint="http://127.0.0.1:8732",
        reward_data_provider="tzkt",
        node_addr_public="https://rpc.tzkt.io/mainnet",
        base_directory="~/pymnt",
        dry_run='signer',
        signer_endpoint="http://127.0.0.1:6732",
        docker=False,
        background_service=False,
        do_not_publish_stats=False,
        verbose="on",
        api_base_url=None,
        retry_injected=False,
        syslog=False,
        log_file="~/pymnt/logs/app.log",
    )

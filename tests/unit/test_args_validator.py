from util.parser import build_parser
from util.args_validator import (
    reward_data_provider_validator,
    network_validator,
    payment_offset_validator,
    initial_cycle_validator,
    release_override_validator,
    base_directory_validator,
    dry_run_validator,
)
import argparse
import pytest
import logging
from Constants import BASE_DIR


LOGGER = logging.getLogger(__name__)


def remove_argument(parser, arg):
    for action in parser._actions:
        opts = action.option_strings
        if (opts and opts[0] == arg) or action.dest == arg:
            parser._remove_action(action)
            break

    for action in parser._action_groups:
        for group_action in action._group_actions:
            if group_action.dest == arg:
                action._group_actions.remove(group_action)
                return


@pytest.mark.parametrize(
    "argument, validator, err_message",
    [
        ('-P', reward_data_provider_validator,
         'args: reward_data_provider argument does not exist'),
        ('-N', network_validator, 'args: network argument does not exist.'),
        ('-D', dry_run_validator, 'args: dry_run argument does not exist.')
    ],
)
def test_reward_data_provider_throws(argument, validator, err_message, caplog):
    caplog.set_level(logging.INFO)
    parser = build_parser()
    parser.set_defaults()
    remove_argument(parser, argument)
    known_args = parser.parse_known_args()[0]
    validator(known_args)
    assert err_message in caplog.text


def test_reward_data_provider_validator(caplog):
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "-P",
        "--reward_data_provider",
        default="BROKEN",
    )
    caplog.set_level(logging.INFO)
    LOGGER = logging.getLogger('info')
    args = argparser.parse_known_args()[0]
    reward_data_provider_validator(args)
    assert 'reward_data_provider BROKEN is not functional at the moment. Please use tzkt or rpc' in caplog.text


def test_network_validator(caplog):
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "-N",
        "--network",
        choices=["MAINNET", "GHOSTNET"],
        default="GHOSTNET",
    )
    caplog.set_level(logging.INFO)
    args = argparser.parse_known_args()[0]
    validator = network_validator(args)
    assert dict(BLOCKS_PER_CYCLE=4096, NAME='GHOSTNET') == validator


def test_payment_offset_validator(caplog, capsys):
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--payment_offset",
        default=-1,
    )
    caplog.set_level(logging.INFO)
    args = argparser.parse_known_args()[0]
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        payment_offset_validator(argparser, args, 400, 'GHOSTNET')
    out, err = capsys.readouterr()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 2
    assert 'error: Valid range for payment offset on GHOSTNET is between 0 and 400' in err


def test_initial_cycle_validator(caplog, capsys):
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--initial_cycle",
        default=-2,
        type=int,
    )
    args = argparser.parse_known_args()[0]
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        initial_cycle_validator(argparser, args)
    out, err = capsys.readouterr()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 2
    assert 'initial_cycle must be in the range of [-1,), default is -1 to start at last released cycle.' in err


def test_release_override_validator(capsys):
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--release_override",
        default=1,
        type=int,
    )
    args = argparser.parse_known_args()[0]
    nb_freeze_cycle = 10
    network = 'GHOSTNET'
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        release_override_validator(argparser, args, nb_freeze_cycle, network)
    out, err = capsys.readouterr()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 2
    assert 'For GHOSTNET, release-override must be -21 (to pay estimated rewards), -10 (to pay frozen rewards) or 0. Default is 0.' in err


def test_base_directory_validator():
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--base_directory",
        default='~/TEST_DIR'
    )
    args = argparser.parse_known_args()[0]
    SUT = base_directory_validator(args)
    assert SUT == argparse.Namespace(
        base_directory='~/TEST_DIR', log_file='~/TEST_DIR/logs/app.log')


def test_base_directory_validator_with_log_file():
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--base_directory",
        default='~/TEST_BASE_DIR'
    )
    argparser.add_argument(
        "--log_file",
        default='~/TEST_LOG_FILE',
    )
    args = argparser.parse_known_args()[0]
    SUT = base_directory_validator(args)
    assert SUT == argparse.Namespace(
        base_directory='~/TEST_BASE_DIR', log_file='~/TEST_LOG_FILE')

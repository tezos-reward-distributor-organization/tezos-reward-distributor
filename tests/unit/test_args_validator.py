from util.parser import (
    build_parser,
    add_argument_provider,
)
from util.args_validator import ArgsValidator, validate
import argparse
import pytest
import logging
from Constants import PUBLIC_NODE_URL


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
        (
            "-P",
            ArgsValidator(argparse.ArgumentParser())._reward_data_provider_validator,
            "args: reward_data_provider argument does not exist",
        ),
        (
            "-N",
            ArgsValidator(argparse.ArgumentParser())._network_validator,
            "args: network argument does not exist.",
        ),
        (
            "-D",
            ArgsValidator(argparse.ArgumentParser())._dry_run_validator,
            "args: dry_run argument does not exist.",
        ),
    ],
)
def validator_throws_if_not_existing(argument, validator, err_message, caplog):
    caplog.set_level(logging.INFO)
    parser = build_parser()
    parser.set_defaults()
    remove_argument(parser, argument)
    validator()
    assert err_message in caplog.text


def test_reward_data_provider_validator():
    argparser = argparse.ArgumentParser()
    add_argument_provider(argparser)
    mock_validator = ArgsValidator(argparser)
    SUT = mock_validator._reward_data_provider_validator()
    assert SUT is True


def test_reward_data_provider_validator_throws(caplog, capsys):
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "-P",
        "--reward_data_provider",
        default="BROKEN",
    )
    caplog.set_level(logging.INFO)
    with pytest.raises(SystemExit) as excinfo:
        mock_validator = ArgsValidator(argparser)
        mock_validator._reward_data_provider_validator()

    out, err = capsys.readouterr()
    assert excinfo.value.code == 2
    assert excinfo.type == SystemExit
    assert "is not functional at the moment. Please use: tzkt, tzstats" in err


def test_payment_offset_validator_throws(caplog, capsys):
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--payment_offset",
        default=-1,
    )
    argparser.add_argument(
        "-N",
        "--network",
        choices=["MAINNET", "GHOSTNET"],
        default="GHOSTNET",
    )
    caplog.set_level(logging.INFO)
    mock_validator = ArgsValidator(argparser)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mock_validator._payment_offset_validator()
    out, err = capsys.readouterr()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 2
    assert "error: Valid range for payment offset on GHOSTNET is" in err


def test_initial_cycle_validator_throws(caplog, capsys):
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--initial_cycle",
        default=-2,
        type=int,
    )
    mock_validator = ArgsValidator(argparser)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mock_validator._initial_cycle_validator()
    out, err = capsys.readouterr()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 2
    assert (
        "initial_cycle must be in the range of [-1,), default is -1 to start at last released cycle."
        in err
    )


def test_release_override_validator_throws(capsys):
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--release_override",
        default=1,
        type=int,
    )
    argparser.add_argument(
        "-N",
        "--network",
        choices=["MAINNET", "GHOSTNET"],
        default="GHOSTNET",
    )
    mock_validator = ArgsValidator(argparser)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mock_validator._release_override_validator()
    out, err = capsys.readouterr()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 2
    assert "For GHOSTNET, release-override must be" in err


def test_base_directory_validator():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--base_directory", default="~/TEST_DIR")
    mock_validator = ArgsValidator(argparser)
    SUT = mock_validator._base_directory_validator()
    assert SUT is True


def test_base_directory_validator_with_log_file():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--base_directory", default="~/TEST_BASE_DIR")
    argparser.add_argument(
        "--log_file",
        default="~/TEST_LOG_FILE",
    )
    mock_validator = ArgsValidator(argparser)
    SUT = mock_validator._base_directory_validator()
    assert SUT is True


def test_validate():
    SUT = validate(build_parser())
    assert SUT == argparse.Namespace(
        initial_cycle=-1,
        run_mode=1,
        release_override=0,
        payment_offset=0,
        network="MAINNET",
        node_endpoint="http://127.0.0.1:8732",
        reward_data_provider="tzkt",
        node_addr_public=PUBLIC_NODE_URL["MAINNET"],
        base_directory="~/pymnt",
        dry_run=False,
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

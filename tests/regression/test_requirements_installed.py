import pytest
from src.main import start_application
from src.launch_common import (
    installed,
    requirements_installed,
)
from unittest.mock import patch, MagicMock


@patch("main.requirements_installed", MagicMock(return_value=False))
@pytest.mark.skip("Protocol Mumbai skip due to branch warning!")
def test_application_aborts_if_requirements_missing():
    """Test if the trd is reliable in handling missing packages
    to not lose valuable transactions.
    Issue:
    https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/issues/407
    """
    assert start_application() == 1


@pytest.mark.skip(
    "Python 3.12 throws error when prompting user for input thus skipping this for now."
)
def test_requirements_installed():
    assert requirements_installed() is True


@patch("src.main.input", MagicMock(return_value="n"))
@patch("src.launch_common.installed", MagicMock(return_value=False))
def test_user_does_not_want_install__missing_package():
    assert requirements_installed("tests/regression/dummy_requirements.txt") is False


@patch("src.main.input", MagicMock(return_value="y"))
@patch("src.launch_common.installed", MagicMock(return_value=False))
def test_user_wants_to_install_missing_not_existent_package():
    assert requirements_installed("tests/regression/dummy_requirements.txt") is False


@patch("src.main.input", MagicMock(return_value="y"))
@patch("src.launch_common.installed", MagicMock(return_value=True))
def test_user_wants_to_install_missing_existent_package():
    assert requirements_installed("tests/regression/dummy_requirements.txt") is False


def test_installed():
    assert installed("pytest")


def test_not_installed():
    assert not installed("some_unknown_random_package_name")

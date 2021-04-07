from launch_common import requirements_installed
from unittest.mock import patch, MagicMock


def test_requirements_installed():
    """Test if the trd is reliable in handeling missing packages
    to not lose valueble transactions.
    Issue:
    https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/issues/407
    """
    assert requirements_installed() is True


@patch('launch_common.input', MagicMock(return_value="n"))
@patch('launch_common.installed', MagicMock(return_value=False))
def test_if_pytest_is_installed():
    assert requirements_installed("tests/regression/dummy_requirements.txt") is False


@patch('launch_common.input', MagicMock(return_value="n"))
@patch('launch_common.installed', MagicMock(return_value=False))
def test_user_does_not_want_install__missing_package():
    assert requirements_installed("tests/regression/dummy_requirements.txt") is False


@patch('launch_common.input', MagicMock(return_value="y"))
@patch('launch_common.installed', MagicMock(return_value=False))
def test_user_wants_to_install_missing_not_existent_package():
    assert requirements_installed("tests/regression/dummy_requirements.txt") is False


@patch('launch_common.input', MagicMock(return_value="y"))
@patch('launch_common.installed', MagicMock(return_value=True))
def test_user_wants_to_install_missing_existent_package():
    assert requirements_installed("tests/regression/dummy_requirements.txt") is False

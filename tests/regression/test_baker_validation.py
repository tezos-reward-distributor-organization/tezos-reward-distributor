from cli.client_manager import ClientManager
from http import HTTPStatus
from unittest.mock import MagicMock, patch

node_endpoint = "http://127.0.0.1:8732"
signer_endpoint = "http://127.0.0.1:6732"

# ============================================================


class Exists_Response:
    def __init__(self):
        self.status_code = HTTPStatus.OK

    def json(self):
        return "edpktqksRnsC4fX1bxWW4DVSdhoirZ1C1RkrEwq4yZabjecmDZLQwS"


@patch(
    "cli.client_manager.ClientManager._do_request",
    MagicMock(return_value=(Exists_Response())),
)
def test_address_is_baker_address_exists():
    baker_address = "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194"  # StakeNow
    client_manager = ClientManager(node_endpoint, signer_endpoint)
    assert client_manager.baker_exists(baker_address) is True


# ============================================================


class Delegatable_Response:
    def __init__(self):
        self.status_code = HTTPStatus.OK

    def json(self):
        return {
            "balance": "151608135131",
            "delegate": "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194",
            "counter": "37410",
        }


@patch(
    "cli.client_manager.ClientManager._do_request",
    MagicMock(return_value=(Delegatable_Response())),
)
def test_address_is_baker_address_delegatable():
    baker_address = "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194"  # StakeNow
    client_manager = ClientManager(node_endpoint, signer_endpoint)
    assert client_manager.baker_delegatable(baker_address) is True


# ============================================================


class Exists_Response:
    def __init__(self):
        self.status_code = HTTPStatus.OK

    def json(self):
        return "edpkuoocAEKZvkjJGRq4jUywMHUWo3CZH12tsdfDiHC3JE4Uyi1So3"


@patch(
    "cli.client_manager.ClientManager._do_request",
    MagicMock(return_value=Exists_Response()),
)
def test_address_is_not_baker_address_exists():
    not_baker_address = "tz1N4UfQCahHkRShBanv9QP9TnmXNgCaqCyZ"  # jdsika
    client_manager = ClientManager(node_endpoint, signer_endpoint)
    assert client_manager.baker_exists(not_baker_address) is True


# ============================================================


class Delegatable_Response:
    def __init__(self):
        self.status_code = HTTPStatus.OK

    def json(self):
        return {
            "balance": "617536",
            "delegate": "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194",
            "counter": "7117399",
        }


@patch(
    "cli.client_manager.ClientManager._do_request",
    MagicMock(return_value=Delegatable_Response()),
)
def test_address_is_not_baker_address_delegatable():
    not_baker_address = "tz1N4UfQCahHkRShBanv9QP9TnmXNgCaqCyZ"  # jdsika
    client_manager = ClientManager(node_endpoint, signer_endpoint)
    assert client_manager.baker_delegatable(not_baker_address) is False


# ============================================================


class Exists_Response:
    def __init__(self):
        self.status_code = HTTPStatus.OK

    def json(self):
        return "123342"


@patch(
    "cli.client_manager.ClientManager._do_request",
    MagicMock(return_value=Exists_Response()),
)
def test_public_key_incorrect():
    not_baker_address = "tz1N4UfQCahHkRShBanv9QP9TnmXNgCaqCyZ"  # jdsika
    client_manager = ClientManager(node_endpoint, signer_endpoint)
    assert client_manager.baker_exists(not_baker_address) is False


# ============================================================


class Exists_Response:
    def __init__(self):
        self.status_code = HTTPStatus.OK

    def json(self):
        return {"balance": "617536", "counter": "7117399"}


@patch(
    "cli.client_manager.ClientManager._do_request",
    MagicMock(return_value=Exists_Response()),
)
def test_not_delegatable():
    not_baker_address = "tz1N4UfQCahHkRShBanv9QP9TnmXNgCaqCyZ"  # jdsika
    client_manager = ClientManager(node_endpoint, signer_endpoint)
    assert client_manager.baker_delegatable(not_baker_address) is False

from os.path import dirname, join
from urllib.parse import urlparse
from unittest.mock import MagicMock
from http import HTTPStatus


class Args:
    """This is a dummy class representing any --arguments passed
    on the command line. You can instantiate this class and then
    change any parameters for testing
    """

    def __init__(
        self,
        initial_cycle,
        reward_data_provider,
        node_addr_public=None,
        api_base_url=None,
    ):
        self.initial_cycle = initial_cycle
        self.run_mode = 3
        self.release_override = 0
        self.payment_offset = 0
        self.network = None
        self.node_endpoint = ""
        self.signer_endpoint = ""
        self.reward_data_provider = reward_data_provider
        self.node_addr_public = node_addr_public
        self.reports_base = join(dirname(__file__), reward_data_provider)
        self.config_dir = dirname(__file__)
        self.dry_run = True
        self.dry_run_no_consumers = True
        self.executable_dirs = dirname(__file__)
        self.docker = False
        self.background_service = False
        self.do_not_publish_stats = False
        self.retry_injected = False
        self.verbose = True
        self.api_base_url = api_base_url


def make_config(baking_address, payment_address, service_fee, min_delegation_amt):
    """This helper function creates a YAML bakers config

    Args:
        baking_address (str): The baking address.
        payment_address (str): The payment address.
        service_fee (float): The service fee.
        min_delegation_amt (int): The minimum amount of deligations.

    Returns:
        str: Yaml file configuration string.
    """
    return """
    baking_address: {:s}
    delegator_pays_ra_fee: true
    delegator_pays_xfer_fee: true
    founders_map:
        tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7: 0.25
        tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace: 0.75
    min_delegation_amt: {:d}
    owners_map:
        tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk: 1.0
    payment_address: {:s}
    reactivate_zeroed: true
    rewards_type: actual
    pay_denunciation_rewards: false
    rules_map:
        tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP: tz1RMmSzPSWPSSaKU193Voh4PosWSZx1C7Hs
        tz1V9SpwXaGFiYdDfGJtWjA61EumAH3DwSyT: TOB
        mindelegation: TOB
    service_fee: {:d}
    specials_map: {{}}
    supporters_set: !!set {{}}
    plugins:
        enabled:
    """.format(
        baking_address, min_delegation_amt, payment_address, service_fee
    )


def mock_request_get(url, timeout):

    path = urlparse(url).path
    # logger.debug("Mock URL: {}".format(path))

    if path == "/chains/main/blocks/head":
        return MagicMock(
            status_code=HTTPStatus.OK,
            json=lambda: {
                "metadata": {
                    "level_info": {
                        "level": 250000,
                        "level_position": 249999,
                        "cycle": 62,
                    }
                }
            },
        )
    if path == "/chains/main/blocks/196609/context/raw/json/cycle/51/roll_snapshot":
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: 10)
    if (
        path
        == "/chains/main/blocks/191232/context/delegates/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V"
    ):
        return MagicMock(
            status_code=HTTPStatus.OK,
            json=lambda: {
                "balance": "15218028669",
                "staking_balance": "191368330803",
                "delegated_contracts": [
                    "tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ",
                    "tz1V9SpwXaGFiYdDfGJtWjA61EumAH3DwSyT",
                    "tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7",
                    "tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace",
                    "tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk",
                    "tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
                    "tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP",
                ],
                "delegated_balance": "176617802134",
            },
        )
    if (
        path
        == "/chains/main/blocks/191232/context/contracts/tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ/balance"
        or path
        == "/chains/main/blocks/head/context/contracts/tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ/balance"
    ):
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "25689884573")
    if (
        path
        == "/chains/main/blocks/191232/context/contracts/tz1V9SpwXaGFiYdDfGJtWjA61EumAH3DwSyT/balance"
        or path
        == "/chains/main/blocks/head/context/contracts/tz1V9SpwXaGFiYdDfGJtWjA61EumAH3DwSyT/balance"
    ):
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "62657825729")
    if (
        path
        == "/chains/main/blocks/191232/context/contracts/tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7/balance"
        or path
        == "/chains/main/blocks/head/context/contracts/tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7/balance"
    ):
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "24916325758")
    if (
        path
        == "/chains/main/blocks/191232/context/contracts/tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace/balance"
        or path
        == "/chains/main/blocks/head/context/contracts/tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace/balance"
    ):
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "55646701807")
    if (
        path
        == "/chains/main/blocks/191232/context/contracts/tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk/balance"
        or path
        == "/chains/main/blocks/head/context/contracts/tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk/balance"
    ):
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "981635036")
    if (
        path
        == "/chains/main/blocks/191232/context/contracts/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V/balance"
        or path
        == "/chains/main/blocks/head/context/contracts/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V/balance"
    ):
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "30527208")
    if (
        path
        == "/chains/main/blocks/191232/context/contracts/tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP/balance"
        or path
        == "/chains/main/blocks/head/context/contracts/tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP/balance"
    ):
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "6725429231")
    if path == "/chains/main/blocks/225280/metadata":
        return MagicMock(
            status_code=HTTPStatus.OK,
            json=lambda: {
                "balance_updates": [
                    {
                        "kind": "freezer",
                        "category": "deposits",
                        "delegate": "tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
                        "cycle": 51,
                        "change": "-14272000000",
                    },
                    {
                        "kind": "freezer",
                        "category": "fees",
                        "delegate": "tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
                        "cycle": 51,
                        "change": "-8374",
                    },
                    {
                        "kind": "freezer",
                        "category": "rewards",
                        "delegate": "tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
                        "cycle": 51,
                        "change": "-354166658",
                    },
                    {
                        "kind": "contract",
                        "contract": "tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
                        "change": "14626175032",
                    },
                ]
            },
        )
    if path == "/chains/main/blocks/196609/helpers/baking_rights":
        # return empty list - not accurate for estimated reward calculation.
        # However, we do not test for this. We just have to return something
        # so the model gets filled with data.
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: [])
    if path == "/chains/main/blocks/196609/helpers/endorsing_rights":
        # return emtpy list - same comment as above
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: [])

    raise Exception("Mocked URL not found")


class Constants:
    NORMAL_TEZOS_ADDRESS = "tz1N4UfQCahHkRShBanv9QP9TnmXNgCaqCyZ"
    STAKENOW_ADDRESS = "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194"

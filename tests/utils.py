import json
import os
from os.path import dirname, join, normpath
from urllib.parse import urlparse
from unittest.mock import MagicMock
from http import HTTPStatus
from model.reward_provider_model import RewardProviderModel
from typing import Optional
from src.Constants import (
    CONFIG_DIR,
    DEFAULT_LOG_FILE,
    TEMP_TEST_DATA_DIR,
)
from src.util.exit_program import exit_program, ExitCode


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
        self.adjusted_early_payouts = False
        self.payment_offset = 0
        self.network = None
        self.node_endpoint = ""
        self.signer_endpoint = ""
        self.reward_data_provider = reward_data_provider
        self.node_addr_public = node_addr_public
        self.base_directory = join(
            dirname(__file__), normpath(TEMP_TEST_DATA_DIR), reward_data_provider
        )
        self.config_dir = join(self.base_directory, normpath(CONFIG_DIR))
        self.log_file = join(self.base_directory, normpath(DEFAULT_LOG_FILE))
        self.dry_run = True
        self.executable_dirs = dirname(__file__)
        self.docker = False
        self.background_service = False
        self.do_not_publish_stats = False
        self.retry_injected = False
        self.verbose = True
        self.api_base_url = api_base_url


def make_config(
    baking_address,
    payment_address,
    service_fee,
    min_delegation_amt,
    min_payment_amt,
):
    """This helper function creates a YAML bakers config

    Args:
        baking_address (str): The baking address.
        payment_address (str): The payment address.
        service_fee (float): The service fee.
        min_delegation_amt (int): The minimum amount of deligations.
        min_payment_amt (int): The minimum amount of payments.

    Returns:
        str: Yaml file configuration string.
    """
    return """
    baking_address: {:s}
    delegator_pays_ra_fee: true
    delegator_pays_xfer_fee: true
    founders_map:
        tz3ipHZQpBBFuxv7eKoFgGnTaU3RBhnS93yY: 0.25
        tz3dKooaL9Av4UY15AUx9uRGL5H6YyqoGSPV: 0.75
    min_delegation_amt: {:d}
    min_payment_amt: {:d}
    owners_map:
        tz3h7UCrLoFih8nrStVy8GcChtZiVuu1mDYD: 1.0
    payment_address: {:s}
    reactivate_zeroed: true
    rewards_type: actual
    pay_denunciation_rewards: false
    rules_map:
        tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP: tz1RMmSzPSWPSSaKU193Voh4PosWSZx1C7Hs
        tz3h7UCrLoFih8nrStVy8GcChtZiVuu1mDYD: TOB
        mindelegation: TOB
    service_fee: {:f}
    specials_map: {{}}
    supporters_set: !!set {{}}
    plugins:
        enabled:
    """.format(
        baking_address,
        min_delegation_amt,
        min_payment_amt,
        payment_address,
        service_fee,
    )


def mock_request_get(url, timeout, **kwargs):
    path = urlparse(url).path
    # print("Mock URL: {}".format(path))

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
    if path == "/chains/main/blocks/2035713/context/raw/json/cycle/500/roll_snapshot":
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: 10)
    if path in [
        "/chains/main/blocks/250000/context/delegates/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
        "/chains/main/blocks/191232/context/delegates/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
        "/chains/main/blocks/195328/context/delegates/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
        "/chains/main/blocks/2034432/context/delegates/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
        "/chains/main/blocks/2035713/context/delegates/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
    ]:
        return MagicMock(
            status_code=HTTPStatus.OK,
            json=lambda: {
                "balance": "15218028669",
                "delegating_balance": "191368330803",
                "delegated_contracts": [
                    "tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ",
                    "tz3h7UCrLoFih8nrStVy8GcChtZiVuu1mDYD",
                    "tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7",
                    "tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace",
                    "tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk",
                    "tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
                    "tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP",
                ],
                "delegated_balance": "176617802134",
            },
        )
    if path in [
        "/chains/main/blocks/250000/context/contracts/tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ/balance",
        "/chains/main/blocks/195328/context/contracts/tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ/balance",
        "/chains/main/blocks/191232/context/contracts/tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ/balance",
        "/chains/main/blocks/head/context/contracts/tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ/balance",
        "/chains/main/blocks/2034432/context/contracts/tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ/balance",
        "/chains/main/blocks/2035713/context/contracts/tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ/balance",
    ]:
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "25689884573")
    if path in [
        "/chains/main/blocks/250000/context/contracts/tz3h7UCrLoFih8nrStVy8GcChtZiVuu1mDYD/balance",
        "/chains/main/blocks/191232/context/contracts/tz3h7UCrLoFih8nrStVy8GcChtZiVuu1mDYD/balance",
        "/chains/main/blocks/head/context/contracts/tz3h7UCrLoFih8nrStVy8GcChtZiVuu1mDYD/balance",
        "/chains/main/blocks/2034432/context/contracts/tz3h7UCrLoFih8nrStVy8GcChtZiVuu1mDYD/balance",
        "/chains/main/blocks/195328/context/contracts/tz3h7UCrLoFih8nrStVy8GcChtZiVuu1mDYD/balance",
        "/chains/main/blocks/2035713/context/contracts/tz3h7UCrLoFih8nrStVy8GcChtZiVuu1mDYD/balance",
    ]:
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "62657825729")
    if path in [
        "/chains/main/blocks/250000/context/contracts/tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7/balance",
        "/chains/main/blocks/191232/context/contracts/tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7/balance",
        "/chains/main/blocks/head/context/contracts/tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7/balance",
        "/chains/main/blocks/2034432/context/contracts/tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7/balance",
        "/chains/main/blocks/195328/context/contracts/tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7/balance",
        "/chains/main/blocks/2035713/context/contracts/tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7/balance",
    ]:
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "24916325758")
    if path in [
        "/chains/main/blocks/250000/context/contracts/tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace/balance",
        "/chains/main/blocks/191232/context/contracts/tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace/balance",
        "/chains/main/blocks/head/context/contracts/tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace/balance",
        "/chains/main/blocks/2034432/context/contracts/tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace/balance",
        "/chains/main/blocks/195328/context/contracts/tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace/balance",
        "/chains/main/blocks/2035713/context/contracts/tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace/balance",
    ]:
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "55646701807")
    if path in [
        "/chains/main/blocks/250000/context/contracts/tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk/balance",
        "/chains/main/blocks/191232/context/contracts/tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk/balance",
        "/chains/main/blocks/195328/context/contracts/tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk/balance",
        "/chains/main/blocks/head/context/contracts/tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk/balance",
        "/chains/main/blocks/2034432/context/contracts/tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk/balance",
        "/chains/main/blocks/2035713/context/contracts/tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk/balance",
    ]:
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "981635036")
    if path in [
        "/chains/main/blocks/250000/context/contracts/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V/balance",
        "/chains/main/blocks/191232/context/contracts/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V/balance",
        "/chains/main/blocks/195328/context/contracts/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V/balance",
        "/chains/main/blocks/head/context/contracts/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V/balance",
        "/chains/main/blocks/2034432/context/contracts/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V/balance",
        "/chains/main/blocks/2035713/context/contracts/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V/balance",
    ]:
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "30527208")
    if path in [
        "/chains/main/blocks/250000/context/contracts/tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP/balance",
        "/chains/main/blocks/191232/context/contracts/tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP/balance",
        "/chains/main/blocks/195328/context/contracts/tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP/balance",
        "/chains/main/blocks/head/context/contracts/tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP/balance",
        "/chains/main/blocks/2034432/context/contracts/tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP/balance",
        "/chains/main/blocks/2035713/context/contracts/tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP/balance",
    ]:
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "6725429231")
    if path in [
        "/chains/main/blocks/225280/metadata",
        "/chains/main/blocks/212992/metadata",
        "/chains/main/blocks/2052096/metadata",
        "/chains/main/blocks/4374528/metadata",
    ]:
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
    if path in [
        "/chains/main/blocks/196609/helpers/baking_rights",
        "/chains/main/blocks/2035713/helpers/baking_rights",
        "/chains/main/blocks/head/helpers/baking_rights",
    ]:
        # return empty list - not accurate for estimated reward calculation.
        # However, we do not test for this. We just have to return something
        # so the model gets filled with data.
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: [])
    if path == "/chains/main/blocks/196609/helpers/endorsing_rights":
        # return emtpy list - same comment as above
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: [])

    if path in [
        "/chains/main/blocks/head/context/raw/json/cycle/557/total_active_stake"
    ]:
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "714705251070165")

    if path in [
        "/chains/main/blocks/head/context/raw/json/cycle/557/selected_stake_distribution"
    ]:
        return MagicMock(
            status_code=HTTPStatus.OK,
            json=lambda: [
                {
                    "baker": "tz1irJKkXS2DBWkU1NnmFQx1c1L7pbGg4yhk",
                    "active_stake": "113536492278227",
                },
                {
                    "baker": "tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
                    "active_stake": "46585432313415",
                },
            ],
        )

    if path in [
        "/chains/main/blocks/head/context/delegates/tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V"
    ]:
        return MagicMock(
            status_code=HTTPStatus.OK,
            json=lambda: {
                "full_balance": "1474309958894",
                "current_frozen_deposits": "1469667294622",
                "frozen_deposits": "1469667294622",
                "delegating_balance": "14813298160131",
                "delegated_contracts": [
                    "tz2XZdnto54v6riWaJEw4ZzCJpVn9SQuxY88",
                    "tz2Eepwyt8UobaWZAKkbnMDgjUq8Nsc8NFiH",
                ],
                "delegated_balance": "13338988201237",
                "deactivated": False,
                "grace_period": 564,
                "voting_power": "14811963201894",
                "remaining_proposals": 20,
                "active_consensus_key": "tz1fPKAtsYydh4f1wfWNfeNxWYu72TmM48fu",
            },
        )

    if path in [
        "/chains/main/blocks/head/context/contracts/tz2XZdnto54v6riWaJEw4ZzCJpVn9SQuxY88/balance",
        "/chains/main/blocks/head/context/contracts/tz2Eepwyt8UobaWZAKkbnMDgjUq8Nsc8NFiH/balance",
    ]:
        return MagicMock(status_code=HTTPStatus.OK, json=lambda: "9108283")

    if path in [
        "/chains/main/blocks/2981888/metadata",
    ]:
        return MagicMock(
            status_code=HTTPStatus.OK,
            json=lambda: {
                "balance_updates": [
                    {
                        "kind": "freezer",
                        "category": "deposits",
                        "delegate": "tz2XZdnto54v6riWaJEw4ZzCJpVn9SQuxY88",
                        "cycle": 51,
                        "change": "-14272000000",
                    },
                    {
                        "kind": "freezer",
                        "category": "fees",
                        "delegate": "tz2XZdnto54v6riWaJEw4ZzCJpVn9SQuxY88",
                        "cycle": 51,
                        "change": "-8374",
                    },
                    {
                        "kind": "freezer",
                        "category": "rewards",
                        "delegate": "tz2XZdnto54v6riWaJEw4ZzCJpVn9SQuxY88",
                        "cycle": 51,
                        "change": "-354166658",
                    },
                    {
                        "kind": "contract",
                        "contract": "tz2XZdnto54v6riWaJEw4ZzCJpVn9SQuxY88",
                        "change": "14626175032",
                    },
                ]
            },
        )

    raise Exception(f"Mocked URL not found for path: {path}")


class Constants:
    MAINNET_ADDRESS_DELEGATOR = "tz1N4UfQCahHkRShBanv9QP9TnmXNgCaqCyZ"
    MAINNET_ADDRESS_STAKENOW_BAKER = "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194"
    MAINNET_ADDRESS_BAKEXTZ4ME_BAKER = "tz1NRGxXV9h6SdNaZLcgmjuLx3hyy2f8YoGN"
    GHOSTNET_ADDRESS_STAKENOW_BAKER = "tz1iZ9LkpAhN8X1L6RpBtfy3wxpEWzFrXz8j"
    MAINNET_ADDRESS_BAKEXTZ4ME_PAYOUT = "tz1PayTZoKjNyofxFQxkzhcv9RCdyW7Q64Wc"

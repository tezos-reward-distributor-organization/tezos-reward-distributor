from os.path import dirname, join


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
    rules_map:
        tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP: tz1RMmSzPSWPSSaKU193Voh4PosWSZx1C7Hs
        tz1V9SpwXaGFiYdDfGJtWjA61EumAH3DwSyT: TOB
        mindelegation: TOB
    service_fee: {:d}
    specials_map: {{}}
    supporters_set: !!set {{}}
    plugins:
    enabled:""".format(
        baking_address, min_delegation_amt, payment_address, service_fee
    )

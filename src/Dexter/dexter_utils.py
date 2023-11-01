from parse import parse

from log_config import main_logger

logger = main_logger


def get_dexter_balance_map(contract_id, snapshot_block, api_provider):
    big_map_id = api_provider.get_big_map_id(contract_id)
    listLPs = api_provider.get_liquidity_providers_list(big_map_id, snapshot_block)
    balanceMap = {}
    totalLiquidity = 0
    for LP in listLPs:
        balanceMap[LP] = {"liquidity_share": listLPs[LP]}
        totalLiquidity += listLPs[LP]
    api_provider.update_current_balances_dexter(balanceMap)
    return balanceMap, totalLiquidity


def process_original_delegators_map(
    delegator_map, contract_id, snapshot_block, api_provider
):
    contract_balance = delegator_map[contract_id]["staking_balance"]
    dexter_liquidity_provider_map, totalLiquidity = get_dexter_balance_map(
        contract_id, snapshot_block, api_provider
    )

    del delegator_map[contract_id]

    for delegator in dexter_liquidity_provider_map:
        balance = int(
            dexter_liquidity_provider_map[delegator]["liquidity_share"]
            * contract_balance
            / totalLiquidity
        )
        if delegator in delegator_map:
            delegator_map[delegator]["staking_balance"] += balance
        else:
            delegator_map[delegator] = {}
            delegator_map[delegator]["staking_balance"] = balance
            delegator_map[delegator]["current_balance"] = dexter_liquidity_provider_map[
                delegator
            ]["current_balance"]
            delegator_map[delegator]["originaladdress"] = contract_id


def parse_dexter_storage(storage_input):
    """
    Dexter Exchange Contract represents a liquidity pool contract and has the following form
    storage (pair (big_map %accounts (address :owner)
                                 (pair (nat :balance)
                                       (map (address :spender)
                                            (nat :allowance))))
              (pair (pair (bool :selfIsUpdatingTokenPool)
                          (pair (bool :freezeBaker)
                                (nat :lqtTotal)))
                    (pair (pair (address :manager)
                                (address :tokenAddress))
                          (pair (nat :tokenPool)
                                (mutez :xtzPool)))));
    """
    storage = {}
    try:  # Json map format
        storage["big_map_id"] = storage_input["args"][0]["int"]

        storage["selfIsUpdatingTokenPool"] = storage_input["args"][1]["args"][0][
            "args"
        ][0]["prim"]

        storage["freezeBaker"] = storage_input["args"][1]["args"][0]["args"][1]["args"][
            0
        ]["prim"]
        storage["lqtTotal"] = storage_input["args"][1]["args"][0]["args"][1]["args"][1][
            "int"
        ]

        storage["manager"] = storage_input["args"][1]["args"][1]["args"][0]["args"][0][
            "string"
        ]
        storage["tokenAddress"] = storage_input["args"][1]["args"][1]["args"][0][
            "args"
        ][1]["string"]
        storage["tokenPool"] = storage_input["args"][1]["args"][1]["args"][1]["args"][
            0
        ]["int"]
        storage["xtzPool"] = storage_input["args"][1]["args"][1]["args"][1]["args"][0][
            "int"
        ]

        return storage

    except Exception:
        try:  # storage through rpc query
            data = parse(
                'Pair {} (Pair (Pair {} (Pair {} {})) (Pair (Pair "{}" "{}") (Pair {} {})))',
                storage_input,
            )
            storage_fields = [
                "big_map_id",
                "selfIsUpdatingTokenPool",
                "freezeBaker",
                "lqtTotal",
                "manager",
                "tokenAddress",
                "tokenPool",
                "xtzPool",
            ]
            for i in range(len(storage_fields)):
                storage[storage_fields[i]] = data[i]
            return storage
        except Exception:
            logger.warn("Parsing dexter storage not successful")
            return storage

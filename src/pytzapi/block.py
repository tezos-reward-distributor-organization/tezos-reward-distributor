class BlockHeader:
    level = None
    proto = None
    predecessor = None
    timestamp = None
    validation_pass = None
    operations_hash = None
    fitness = []
    context = None
    priority = None
    proof_of_work_nonce = None
    seed_nonce_hash = None
    signature = None

    def __init__(self):
        pass


class BlockMetadataLevel:
    """
        attributes:
            cycle           : cycle
            cycle_position  : cycle position in range [0, nb_blocks_per_cycle)
            level_position  : cycle * nb_blocks_per_cycle + cycle_position
            level           : level_position + 1
    """
    level = None
    level_position = None
    cycle = None
    cycle_position = None
    voting_period = None
    voting_period_position = None
    expected_commitment = None

    def __init__(self):
        pass


class BlockMetadata:
    protocol = None
    next_protocol = None
    test_chain_status = {}
    max_operations_ttl = None
    max_operation_data_length = None
    max_block_header_length = None
    max_operation_list_length = list(dict())
    baker = None
    level = BlockMetadataLevel()
    voting_period_kind = None
    nonce_hash = None
    consumed_gas = None
    deactivated = []
    balance_updates = []

    def __init__(self):
        pass

class Block:
    protocol = None
    chain_id = None
    hash = None
    header = BlockHeader()
    metadata = BlockMetadata()
    operations = []

    def __init__(self) -> None:
        pass

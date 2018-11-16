# todo: replace with rpc client rpc get /chains/main/blocks/head/context/constants
network_config_map = {
    'MAINNET': {'NAME': 'MAINNET', 'NB_FREEZE_CYCLE': 5, 'BLOCK_TIME_IN_SEC': 60, 'BLOCKS_PER_CYCLE': 4096},
    'ALPHANET': {'NAME': 'ALPHANET', 'NB_FREEZE_CYCLE': 2, 'BLOCK_TIME_IN_SEC': 30, 'BLOCKS_PER_CYCLE': 2048},
    'ZERONET': {'NAME': 'ZERONET', 'NB_FREEZE_CYCLE': 5, 'BLOCK_TIME_IN_SEC': 20, 'BLOCKS_PER_CYCLE': 128},
}

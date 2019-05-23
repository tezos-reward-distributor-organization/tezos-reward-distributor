from log_config import main_logger
from util.rpc_utils import parse_json_response
import requests

logger = main_logger

default_network_config_map = {
    'MAINNET': {'NAME': 'MAINNET', 'NB_FREEZE_CYCLE': 5, 'BLOCK_TIME_IN_SEC': 60, 'BLOCKS_PER_CYCLE': 4096, 'BLOCKS_PER_ROLL_SNAPSHOT':256},
    'ALPHANET': {'NAME': 'ALPHANET', 'NB_FREEZE_CYCLE': 3, 'BLOCK_TIME_IN_SEC': 30, 'BLOCKS_PER_CYCLE': 2048, 'BLOCKS_PER_ROLL_SNAPSHOT':256},
    'ZERONET': {'NAME': 'ZERONET', 'NB_FREEZE_CYCLE': 5, 'BLOCK_TIME_IN_SEC': 20, 'BLOCKS_PER_CYCLE': 128, 'BLOCKS_PER_ROLL_SNAPSHOT':8},
}

CONSTANTS_COMM = "rpc get http://{}/chains/main/blocks/head/context/constants"
URL = "https://{}.tzbeta.net/chains/main/blocks/head/context/constants"
url_prefix = {"MAINNET" : "rpc", "ALPHANET" : "rpcalpha", "ZERONET" : "rpczero"}

def init_network_config(network_name, config_client_manager, node_addr):
    network_config_map = {}    
    try:
        network_config_map[network_name] = get_network_config_from_local_node(config_client_manager, node_addr)
        network_config_map[network_name]['NAME'] = network_name
        logger.debug("Network configuration constants successfully loaded from a local node.")
        return network_config_map
    except:
        logger.debug("Failed to get network configuration constants from a local node.")
    
    try:
        network_config_map[network_name] = get_network_config_from_public_node(network_name)
        network_config_map[network_name]['NAME'] = network_name
        logger.debug("Network configuration constants successfully loaded from a public node.")
        return network_config_map
    except:
        logger.debug("Failed to get network configuration constants from a public node.")
    
    logger.debug("Default network configuration constants will be used.")
    return default_network_config_map



def get_network_config_from_local_node(config_client_manager, node_addr):
    request_constants = CONSTANTS_COMM.format(node_addr)
    response_constants = config_client_manager.send_request(request_constants)
    constants = parse_json_response(response_constants)
    network_config_map = parse_constants(constants)
    return network_config_map


def get_network_config_from_public_node(network_name):
    url = URL.format(url_prefix[network_name])
    response_constants = requests.get(url, timeout=5)
    constants = response_constants.json()
    network_config_map = parse_constants(constants)
    return network_config_map
    
def parse_constants(constants):
    network_config_map = {}
    network_config_map['NB_FREEZE_CYCLE'] = int(constants['preserved_cycles'])    
    network_config_map['BLOCK_TIME_IN_SEC'] = int(constants['time_between_blocks'][0])
    network_config_map['BLOCKS_PER_CYCLE'] = int(constants['blocks_per_cycle'])
    network_config_map['BLOCKS_PER_ROLL_SNAPSHOT'] = int(constants['blocks_per_roll_snapshot'])
    return network_config_map
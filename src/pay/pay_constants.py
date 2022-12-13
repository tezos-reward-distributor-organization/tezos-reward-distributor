# General transaction parameters:
#
# This fee limit is set to allow payouts to ovens
# Other KT accounts with higher fee requirements will be skipped
# TODO: define set of known contract formats and make this fee for unknown contracts configurable
KT1_FEE_SAFETY_CHECK = False
FEE_LIMIT_CONTRACTS = 100000
ZERO_THRESHOLD = 1  # too less to payout in mutez
MAX_TX_PER_BLOCK_TZ = 550
MAX_TX_PER_BLOCK_KT = 25

# For simulation
# https://rpc.tzkt.io/mainnet/chains/main/blocks/head/context/constants
HARD_GAS_LIMIT_PER_OPERATION = 1040000
HARD_STORAGE_LIMIT_PER_OPERATION = 60000
COST_PER_BYTE = 250
MINIMUM_FEE_MUTEZ = 100
MUTEZ_PER_GAS_UNIT = 0.1
MUTEZ_PER_BYTE = 1

PKH_LENGTH = 36
SIGNATURE_BYTES_SIZE = 64
MAX_NUM_TRIALS_PER_BLOCK = 2
MAX_BLOCKS_TO_CHECK_AFTER_INJECTION = 5
MAX_BATCH_PAYMENT_ATTEMPTS = 3

COMM_DELEGATE_BALANCE = "/chains/main/blocks/{}/context/contracts/{}/balance"
COMM_PAYMENT_HEAD = "/chains/main/blocks/head~10"
COMM_HEAD = "/chains/main/blocks/head"
COMM_COUNTER = "/chains/main/blocks/head/context/contracts/{}/counter"
CONTENT = '{"kind":"transaction","source":"%SOURCE%","destination":"%DESTINATION%","fee":"%fee%","counter":"%COUNTER%","gas_limit":"%gas_limit%","storage_limit":"%storage_limit%","amount":"%AMOUNT%"}'
FORGE_JSON = '{"branch": "%BRANCH%","contents":[%CONTENT%]}'
RUNOPS_JSON = '{"branch": "%BRANCH%","contents":[%CONTENT%], "signature":"edsigtXomBKi5CTRf5cjATJWSyaRvhfYNHqSUGrn4SdbYRcGwQrUGjzEfQDTuqHhuA8b2d8NarZjz8TRf65WkpQmo423BtomS8Q"}'
PREAPPLY_JSON = '[{"protocol":"%PROTOCOL%","branch":"%BRANCH%","contents":[%CONTENT%],"signature":"%SIGNATURE%"}]'
JSON_WRAP = '{"operation": %JSON%,"chain_id":"%chain_id%"}'

COMM_RUNOPS = "/chains/main/blocks/head/helpers/scripts/run_operation"
COMM_FORGE = "/chains/main/blocks/head/helpers/forge/operations"
COMM_PREAPPLY = "/chains/main/blocks/head/helpers/preapply/operations"
COMM_INJECT = "/injection/operation"
COMM_WAIT = "/chains/main/blocks/%BLOCK_HASH%/operation_hashes"

# These values may change with protocol upgrades
TX_FEES = {
    "TZ1_TO_ALLOCATED_TZ1": {
        "FEE": 298,
        "GAS_LIMIT": 1451,
        "STORAGE_LIMIT": 0,  # 65 mutez before
    },
    "TZ1_TO_NON_ALLOCATED_TZ1": {
        "FEE": 397,
        "GAS_LIMIT": 1421,
        "STORAGE_LIMIT": 277,
        "BURN_FEE": None,  # 0.257 tez before
    },
    "TZ1_REVEAL": {
        "FEE": 357,
        "GAS_LIMIT": 1000,
        "STORAGE_LIMIT": 0,
    },
}

import json
constants = """Warning:
  
                 This is NOT the Tezos Mainnet.
  
      The node you are connecting to claims to be running on the
                 Tezos Zeronet DEVELOPMENT NETWORK.
           Do NOT use your fundraiser keys on this network.
  Zeronet is a testing network, with free tokens and frequent resets.

{ "proof_of_work_nonce_size": 8, "nonce_length": 32,
  "max_revelations_per_block": 32, "max_operation_data_length": 16384,
  "preserved_cycles": 5, "blocks_per_cycle": 128,
  "blocks_per_commitment": 32, "blocks_per_roll_snapshot": 8,
  "blocks_per_voting_period": 32768, "time_between_blocks": [ "20" ],
  "endorsers_per_block": 32, "hard_gas_limit_per_operation": "4000000",
  "hard_gas_limit_per_block": "40000000",
  "proof_of_work_threshold": "70368744177663",
  "tokens_per_roll": "10000000000", "michelson_maximum_type_size": 1000,
  "seed_nonce_revelation_tip": "125000", "origination_burn": "257000",
  "block_security_deposit": "512000000",
  "endorsement_security_deposit": "64000000", "block_reward": "16000000",
  "endorsement_reward": "2000000", "cost_per_byte": "1000",
  "hard_storage_limit_per_operation": "600000" } """

protocols = """
Warning:
  
                 This is NOT the Tezos Mainnet.
  
      The node you are connecting to claims to be running on the
                 Tezos Zeronet DEVELOPMENT NETWORK.
           Do NOT use your fundraiser keys on this network.
  Zeronet is a testing network, with free tokens and frequent resets.

[ "ProtoDemoDemoDemoDemoDemoDemoDemoDemoDemoDemoD3c8k9",
  "ProtoALphaALphaALphaALphaALphaALphaALphaALphaDdp3zK",
  "ProtoGenesisGenesisGenesisGenesisGenesisGenesk612im" ]
"""


hash="""
zeronet: Pulling from tezos/tezos
Digest: sha256:9ab0e991b4a17d879e8f52b045e50b0d79293da3f82447de08182dcb207053f1
Status: Image is up to date for tezos/tezos:zeronet
Warning:
  
                 This is NOT the Tezos Mainnet.
  
      The node you are connecting to claims to be running on the
                 Tezos Zeronet DEVELOPMENT NETWORK.
           Do NOT use your fundraiser keys on this network.
  Zeronet is a testing network, with free tokens and frequent resets.

"BMeLBs4C2RbZos4anjmGvP3GMa6hA7froTpxZN7HsNtRZyvK72r"
"""

def strip_disclaimer(client_response):


    idx = client_response.find("{")
    if idx<0:
        idx = client_response.find("[")
    if idx<0:
        idx = client_response.find("\"")
    if idx<0:
        raise Exception("Unknown client response format")

    response_str=client_response[idx:]

    print(response_str)

    response_json = json.loads(response_str)
    return response_json

response_json = strip_disclaimer(constants)
print("blocks_per_cycle is {} ".format(response_json['blocks_per_cycle']))
print("preserved_cycles is {} ".format(response_json['preserved_cycles']))
print("time_between_blocks is {} ".format(response_json['time_between_blocks'][0]))

response_json = strip_disclaimer(protocols)
print("active protocol is {} ".format(response_json[0]))

response_json= strip_disclaimer(hash)
print("active branch is {}".format(response_json))
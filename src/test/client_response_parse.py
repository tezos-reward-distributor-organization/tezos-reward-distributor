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

test_str = """
Warning:

                           This is NOT the Tezos Mainnet.
                        The Tezos Mainnet is not yet released.

              The node you are connecting to claims to be running on the
                        Tezos Betanet EXPERIMENTAL NETWORK.
      Betanet is a pre-release experimental network and comes with no warranty.
              Use your fundraiser keys on this network AT YOUR OWN RISK.
    All transactions happening on the Betanet are expected to be valid in the Mainnet.
            If in doubt, we recommend that you wait for the Mainnet lunch.

Error:
  Rpc request failed:
     - meth: POST
     - uri: http://localhost:8732/chains/main/blocks/head/helpers/preapply/operations
     - error: Oups! It looks like we forged an invalid HTTP request.
                [ { "protocol": "PsYLVpVvgbLhAhoqAkMFUo6gudkJ9weNXhUYCiLDzcUpFpkk8Wt",
    "branch": "BLh62ZiNsBiLnQZiuUsQzTdXkjWgeLAMryYJywV9z4wCZsjTL8h",
    "contents":
      [ { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT1PEZ91VnphKodWSfuvCcjXrA29zfHsgUxt", "fee": "0",
          "counter": "316261", "gas_limit": "200", "storage_limit": "0",
          "amount": "31431000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT1Ao8UXNJ9Dz71Wx3m8yzYNdnNQp2peqtMc", "fee": "0",
          "counter": "316262", "gas_limit": "200", "storage_limit": "0",
          "amount": "3117000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT18bVwvyLBR1GAM1rBoiHzEXVNtXb5C3vEU", "fee": "0",
          "counter": "316263", "gas_limit": "200", "storage_limit": "0",
          "amount": "2830000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT1HuhLZ3Rg45bRnSVssA6KEVXqbKbjzsmPH", "fee": "0",
          "counter": "316264", "gas_limit": "200", "storage_limit": "0",
          "amount": "1000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT18bVwvyLBR1GAM1rBoiHzEXVNtXb5C3vEU", "fee": "0",
          "counter": "316265", "gas_limit": "200", "storage_limit": "0",
          "amount": "40000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT1PEZ91VnphKodWSfuvCcjXrA29zfHsgUxt", "fee": "0",
          "counter": "316266", "gas_limit": "200", "storage_limit": "0",
          "amount": "431000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT18bVwvyLBR1GAM1rBoiHzEXVNtXb5C3vEU", "fee": "0",
          "counter": "316267", "gas_limit": "200", "storage_limit": "0",
          "amount": "75000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT1PEZ91VnphKodWSfuvCcjXrA29zfHsgUxt", "fee": "0",
          "counter": "316268", "gas_limit": "200", "storage_limit": "0",
          "amount": "75000" } ],
    "signature":
      "edsigtiGP1KZTXrjwbUtNB2FiLKLD4zttATB73XGpkPcvicfMnSo7wBgQiWDUKh9aaeLsQywNVGBRW8aTF8Jh9PmwkCn6BF6b" } ]
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
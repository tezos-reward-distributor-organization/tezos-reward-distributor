# baker's bussiness parameters

# baker's 'tz' address, NOT A KT address
BAKING_ADDRESS = "tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj"

# standard fee that is valid for everybody
STANDARD_FEE=0

# Minimum delegation amount (in Tez)
MIN_DELEGATION_AMT=0

# founders that shares the profits. map of founder payment address and share of the profit. Shares should sum up to 1.
founders_map={"tz1MWTkFRXA2dwez4RHJWnDWziLpaN6iDTZ9":1.0}
# deposit owners map of address and deposit ratio which must sum up to 1
owners_map={"KT1MMhmTkUoHez4u58XMZL7NkpU9FWY4QLn2":1.0}
# no fee customers, e.g. founders, supporters
supporters_set={}
# customers with special rates. map of KT address and baking fee
specials_map={}
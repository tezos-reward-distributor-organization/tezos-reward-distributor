# Managing Contribution Payouts

This document serves to instruct how to manage contribution payouts from the TRD multisig address.

### Metadata

* Multisig Address: KT1Hir1o22RGE1Hyrrzpp3rXjhTcoUurSYKu
* Multisig Manager: 
* Authorized Members:
	* edpkvHzFCaC33D8md4UaeX1phuYx3JKLuaTN7ffpQbMHJRAzJr9Mwy
	* edpkuCFk3sw9besfKP9WKB7Nxrj6Di3dgBrKwf74QzTVpDbNWYu911
	* edpkuB12NBMqeyYdT4WDouYZ7EbD7JyJtJ7taP2KYQf68nkkB3ApEf (Krixt)

### Signing Request

Payouts must be signed by 2 of the 3 multisig members before it can be executed on the blockchain.

A multisig member must sign the same transaction using his/her own private key which is authorized on the multisig contract.

	XXX.XX - The amount, in XTZ to transfer
	YYYYYY - The receiver of the funds (ie: tz1...)
	ZZZZZZ - The PKH of the multisig member

    $ octez-client sign multisig transaction on KT1Hir1o22RGE1Hyrrzpp3rXjhTcoUurSYKu transferring XXX.XX to YYYYYY using secret key ZZZZZZ

The output of the above command will be a single signature: `edsigu3WqyPEEYBce5.....`

2 signatures are required to execute the transaction.

### Executing the Payout

With 2, or more, signatures, execute the transaction:

    XXX.XX - The amount, in XTZ to transfer
    YYYYYY - The receiver of the funds (ie: tz1...)
    ZZZZZZ - The PKH of the multisig member
    AAAAAA - Signature from above command
    BBBBBB - Signature from another member

    $ octez-client from multisig contract KT1Hir1o22RGE1Hyrrzpp3rXjhTcoUurSYKu transfer XXX.XX to YYYYYY on behalf of ZZZZZZ with signatures AAAAAA BBBBBB

The transaction will be verified by checking all signatures, and executed on the blockchain.


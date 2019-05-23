<img src="https://raw.githubusercontent.com/habanoz/trd-art/master/logo-narrow/trd_512__1.png" width="128" /> 

## V5 Announcement

V5 is available under pphases branch. It will be merged to master in coming days. Feel free to test it. New version comes with following improvements:
- Better output
- Enhanced calculation steps aka phases
- Ability to exclude owners or founders
- Payment to custom address
- Merging of multiple payments towards an address into single payment
- Ability to choose where rewards of excluded or min delegated accounts go: share among other delegators, send to founders, do nothing e.g. leave in balance.

Check license and notice.txt files for more information. 

## V4 Announcement
With V4 TRD can use tezos node to make calculations. This way, dependency on tzscan is relieved.

## Tezos Reward Distributor : Run & Forget 

DISCLAIMER : TEZOS REWARD DISTRIBUTOR IS PROVIDED AS IS. IT IS UNDER CONSTANT DEVELOPMENT. EVENT THOUGH IT IS WELL TESTED, PLEASE USE WITH CARE. ALWAYS MAKE A PRE-RUN IN DRY MODE BEFORE MAKING ACTUAL PAYMENTS. IF YOU WANT TO RUN IN SERVICE MODE DO IT AFTER YOU ARE CONFIDENT WITH THE APPLICATION AND IN SERVICE MODE DO NOT UPDATE OFTEN.


## Tezos Reward Distributor

A software for distributing baking rewards with delegators. This is not a script but service which can run in the background all the time. It can track cycles and make payments. It does not have to be used as a service, It can also be used interactively. 

Design principals are: 

- Automatic Execution with no manual involvement: Run and forget
- Simplicity: Simple and intuitional parameter configuration. Default values are ready for the most common use case. 
- Covering different use cases: supporters, special rates, future payments, security deposit owned by multiple parties, fee sharing among founders. Choose which cycle to pay and when to stop the application.
- Traceability: CSV payment reports with calculation details. Logs for traking application lifecycle.
- Testability: Dry for seeing results witout making any modification. Support for development networks e.g. zeronet, alphanet.
- Safety: Payment logs for avoiding double payments by mistake. Lock file for avoiding multiple instances running at the same time. Shutdown handlers for avoiding application shutdowns in the middle of a sensitive operation. 

Features:
- Reward calculations based on tzscan API or tezos node RPC interface. 
- Batch Payments
- Email notifications
- Re-attempt failed payments
- Minimal configuration needs, while having many configuration options
- Written in Python. Easy to modify to suit custom needs


### Requirements and Setup:

Python 3 is required. You can use following commands to install. 

```
sudo apt-get update
sudo apt-get -y install python3-pip
```

Download the application repository using git clone:

```
git clone https://github.com/habanoz/tezos-reward-distributor
```

To install required modules, use pip with requirements.txt provided.

```
cd tezos-reward-distributor
pip3 install -r requirements.txt
```

Regulary check and upgrade to the latest available version:

```
git pull
```

### How to Run:

For a list of parameters, run:

```
python3 src/main.py --help
```

The most common use case is to run in mainnet and start to make payments from last released rewards or continue making payments from the cycle last payment is done. 

```
python3 src/main.py
```

For more example commands please see wiki page:

https://github.com/habanoz/tezos-reward-distributor/wiki/How-to-Run


### Baker Configuration:

Each baker has its own configuration and policy. A payment system should be flexible enough to cover needs of bakers. The application uses a yaml file for loading baker specific configurations. 

An example configuration file is present in the repository. For more information on configuration details please see our wiki page:
https://github.com/habanoz/tezos-reward-distributor/wiki/Configuration

TRD is designed to work as a deamon. It expects use of tezos signer for encrypted payment accounts. Unencrypted payment accounts can be used without tezos signer. If a payment account is encrypted and not configured to be signed by tezos signer, TRD will freeze. For more information on payment addresses please refer to our wikipage:
https://github.com/habanoz/tezos-reward-distributor/wiki/Payment-Address

### Linux Service

It is possible to add tezos-reward-distributer as a Linux service. It can run in the background. 

If docker is used, make sure user is in docker group
```
sudo usermod -a -G docker $USER
```

In order to set up the service with default configuration arguments, run the following command:

```
sudo python3 service_add.py
```

For more information please refer to wiki page:

https://github.com/habanoz/tezos-reward-distributor/wiki/Linux-Service


### Email Setup

tezos-reward-distribute will create an email.ini file. Fill this file with your email configuration to send payment emails.

### Fee Setup

fee.ini file contains details about transaction fees. Currently the fee value specified under DEFAULT domain is used as fee amount. It is in mutez. Check the link below to see effect of fee value of 1274.

https://zeronet.tzscan.io/opCnDj8bpr5ACrbLSqy4BDCMsNiY8Y34bvnm2hj7MvcxaRiu5tu


### Contributions
Please refer to contributions guide on wiki pages.

https://github.com/habanoz/tezos-reward-distributor/wiki/How-to-Contribute

### Funding

TRD is an open source project and will stay like this. It is not funded by any organization. A grant request is rejected by Tezos Foundation. However, I will try to continue to enhance the software and support the community.


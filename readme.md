## Tezos Reward Distributor : Run & Forget

DISCLAIMER : TEZOS REWARD DISTRIBUTOR IS PROVIDED AS IS. IT IS UNDER CONSTANT DEVELOPMENT. EVENT THOUGH IT IS WELL TESTED, PLEASE USE WITH CARE. ALWAYS MAKE A PRE-RUN IN DRY MODE BEFORE MAKING ACTUAL PAYMENTS. IF YOU WANT TO RUN IN SERVICE MODE DO IT AFTER YOU ARE CONFIDENT WITH THE APPLICATION AND IN SERVICE MODE DO NOT UPDATE OFTEN.


### Tezos Reward Distributor

A software for distributing baking rewards with delegators. This is not a script but service which can run in the background all the time. It can track cycles and make payments. It does not have to be used as a service, It can also be used interactively. 

Design principals are: 

- Automatic Execution with no manual involvement: Run and forget
- Simplicity: Simple and intuitional parameter configuration. Default values are ready for the most common use case. 
- Covering different use cases: supporters, special rates, future payments, security deposit owned by multiple parties, fee sharing among founders. Choose which cycle to pay and when to stop the application.
- Traceability: CSV payment reports with calculation details. Logs for traking application lifecycle.
- Testability: Dry for seeing results witout making any modification. Support for development networks e.g. zeronet, alphanet.
- Safety: Payment logs for avoiding double payments by mistake. Lock file for avoiding multiple instances running at the same time. Shutdown handlers for avoiding application shutdowns in the middle of a sensitive operation. 

Features:
- Reward calculations based on tzscan API.
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

If this did not work then you can also do this using curl

```
curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
python3 get-pip.py --user
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

Make payments for a single cycle:

```
python3 src/main.py -C 42 -M 3 
```

Make pending payments and stop:

```
python3 src/main.py -M 2
```

Make pending payments beginning from a cycle and stop:

```
python3 src/main.py -C 30 -M 2
```

Run in dry-run mode in zeronet, make payments from cycle 30 and exit:

```
python3 src/main.py -D -N ZERONET -C 30 -M 3
```

### Baker Configuration:

Each baker has its own configuration and policy. A payment system should be flexible enough to cover needs of bakers. The applcation uses a yaml file for loading baker specific configurations. 

An example configuration file is present in the repository. For more information on configuration details please see our wiki page:
https://github.com/habanoz/tezos-reward-distributor/wiki/Configuration

TRD is designed to work as a deamon. It expects use of tezos signer for encrypted payment accounts. Unencrypted payment accounts can be used without tezos signer. If a payment account is encrypted and not configured to be signed by tezos signer, TRD will freeze. For more information on payment addresses please refer to our wikipage:
https://github.com/habanoz/tezos-reward-distributor/wiki/Payment-Address

### Linux Service

It is possible to add tezos-reward-distributer as a Linux service. It can run in the background. In order to set up the service with default configuration arguments, run the following command:

```
sudo python3 service_add.py
```

Note: If you do not want to use the default arguments, append any arguments you wish to change after service_add.py. They will be appended to main.py call.


It will create a service file and use it to enable the service. Once enabled use following commands to start/stop the service.

```
sudo systemctl start tezos-reward.service
sudo systemctl stop tezos-reward.service
```

In order to see service status:

```
systemctl status tezos-reward.service
```

In order to see logs:

```
journalctl --follow --unit=tezos-reward.service
```

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


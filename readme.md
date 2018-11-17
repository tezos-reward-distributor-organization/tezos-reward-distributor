## Tezos Reward Distributor : Run & Forget

A software for distributing baking rewards with delegators. This is not a script but service which can run in the background all the time. It can track cycles and make payments. It does not have to be used as a service, It can also be used interactively. 

Design principals are: 

- Automatic Execution with no manual involvement: Run and forget
- Simplicity: Simple and intuitional parameter configuration. Default values are ready for the most common use case. 
- Covering different use cases: supporters, special rates, future payments, security deposit owned by multiple parties, fee sharing among founders. Choose which cycle to pay and when to stop the application.
- Traceability: CSV payment reports with calculation details. Logs for traking application lifecycle.
- Testability: Dry for seeing results witout making any modification. Support for development networks e.g. zeronet, alphanet.
- Safety: Payment logs for avoiding multiple payments by mistake. Lock file for avoiding multiple instances running at the same time. Shutdown handlers for avoiding application shutdowns in the middle of a sensitive operation. 

Features:
- Reward calculations based on tzscan API.
- Batch Payments
- Email notifications
- Re-attempt failed payments
- Minimal configuration needs, while having many configuration options
- Written in Python. Easy to modify to suit custom needs


### Requirements and Setup:

Python 3 is required. Download the application repository using git clone:

```
git clone https://github.com/habanoz/tezos-reward-distributor
```

To install required modules, use pip with requirements.txt provided.

```
cd tezos-reward-distributer
pip install -r requirements.txt
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

The most common use case is run in mainnet and start to make payments from last released rewards or continue making payments from the cycle last payment is done. Just provide the address/alias to make payments from. 

```
python3 src/main.py mytezospaymentaddress
```

Make payments for a single cycle:

```
python3 src/main.py -C 42 -M 3  mytezospaymentaddress
```

Make pending payments and stop:

```
python3 src/main.py -M 2  mytezospaymentaddress
```

Make pending payments beginning from a cycle and stop:

```
python3 src/main.py -C 30 -M 2 mytezospaymentaddress
```

Run in dry-run mode in zeronet, make payments from cycle 30 and exit:

```
python3 src/main.py -D -N ZERONET -C 30 -M 3 mytezospaymentaddress
```

### Business Configuration:

Business configuration contains baker and delegator specific setting. Edit file BusinessConfiguration.py. Start by setting your baking address. Then set your delegation fee. If there are delegators with special rates, speciy them in specials_map. If your stake is owned by multiple parties specify them in owners_map with ratios. If baker is run by multiple founders set them in founders_map.

Thats all.


### Linux Service

It is possible to add tezos-reward-distributer as a Linux service. It can run in the background. In order to set up the service run following command:

```
sudo python3 service_add.py mytezospaymentaddress
```

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

#### Terms:

- Reward: Coins rewarded by the network for the baking/endorsing operations.
- Payment: Coins paid to delegators after excluding service fee.
- freeze cycle: number of cycles rewards are kept frozen by the tezos network. Can be given negative values to let the application make future payments.

<img src="https://raw.githubusercontent.com/habanoz/trd-art/master/logo-narrow/trd_512__1.png" width="128" /> 

DISCLAIMER: TEZOS REWARD DISTRIBUTOR IS PROVIDED AS IS. IT IS UNDER CONSTANT DEVELOPMENT. EVENT THOUGH IT IS WELL TESTED, PLEASE USE IT WITH CARE. ALWAYS MAKE A PRE-RUN IN DRY MODE BEFORE MAKING ACTUAL PAYMENTS. IF YOU WANT TO RUN IN SERVICE MODE DO IT AFTER YOU ARE CONFIDENT WITH THE APPLICATION. IN SERVICE MODE ONLY UPDATE IF NEEDED.

PRIVACY: TEZOS REWARD DISTRIBUTOR COLLECTS ANONYMOUS STATISTICS. PLEASE READ OUR [STATISTICS POLICY](https://tezos-reward-distributor-organization.github.io/tezos-reward-distributor/statistics.html) FOR MORE INFORMATION.

## Tezos Reward Distributor: Run & Forget

[![Actions Status](https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/workflows/CI/badge.svg)](https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/actions)
[![Documentation Status](https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/workflows/Docs/badge.svg)](https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/actions)
[![Stable Documentation Status](https://img.shields.io/badge/docs-stable-blue.svg)](https://tezos-reward-distributor-organization.github.io/tezos-reward-distributor/)

TRD is a software for distributing staking rewards of Tezos delegators, introduced in detail in this [Medium article](https://medium.com/@huseyinabanox/tezos-reward-distributor-e6588c4d27e7). This is not a script but a full scale application which can continuously run in the background as a Linux service. It can track cycles and make payments. However, it does not have to be used as a service, but it can also be used interactively.

The documentation can be found [here](https://tezos-reward-distributor-organization.github.io/tezos-reward-distributor/). 

You can also ask for support on the TRD channel of the Tezos-Baking Slack group, if you are a member of this group you can view the channel [here](https://tezos-baking.slack.com/messages/CQ35AM8KE), if you are not a member you can [join the group](https://join.slack.com/t/tezos-baking/shared_invite/zt-yqxeszcy-rpvYmBtXr5oewh6M0DFkyQ) and find the trd channel from the channel list or simply [file an issue](https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/issues).

TRD supports complex payments, pays in batches, and supports three backends for calculations: Tezos RPC, [TZPRO API](https://docs.tzpro.io/) and [TzKT API](https://api.tzkt.io/). TRD is developed and tested extensively by the community.

**Provider notes:**

### Blockwatch: TZPRO

The [terms and conditions](https://tzpro.io/terms) of TZPRO note that an account and API key are needed for the use of the API. Please review the [pricing](https://tzpro.io/#pricing) information. For further help contact hello@blockwatch.cc for more information.

In order to use your API key in the application copy and rename the .env.example to .env and add the API key for TZPRO.

### TzKT

The [terms of use](https://api.tzkt.io/#section/Terms-of-Use) of TzKT API allow for commercial and non-commercial use.

> TzKT API is free for everyone and for both commercial and non-commercial usage.
>
> If your application or service uses the TzKT API in any forms: directly on frontend or indirectly on backend, you should mention that fact on your website or
> application by placing the label "Powered by TzKT API" with a direct link to [tzkt.io](https://tzkt.io).

## Requirements and Setup

Python 3 is required. You can use the following commands to install it.

```bash
sudo apt-get update
sudo apt-get -y install python3-pip
```

Download the application repository using git clone:

```bash
git clone https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor
```

To install required modules, use pip with `requirements.txt` provided.

```bash
cd tezos-reward-distributor
pip install -r requirements.txt
```

To install the required modules for developers, use pip with `requirements_developer.txt` provided.

```bash
cd tezos-reward-distributor
pip install -r requirements_developer.txt
```


Regularly check and upgrade to the latest available version:

```bash
git fetch origin #fetches new branches
git status #see the changes
git pull
```

## Sample configuration

Before running TRD, you need to configure it by adding your baker's address and payout settings.
The configuration file should be included in the `~/pymnt/cfg/` directory by default. You can use the following command to copy and modify the example configuration:

```bash
# create directory
mkdir -p ~/pymnt/cfg/
cp tezos-reward-distributor/examples/tz1boot1pK9h2BVGXdyvfQSv8kd1LQM6H889.yaml ~/pymnt/cfg/
nano ~/pymnt/cfg/tz1boot1pK9h2BVGXdyvfQSv8kd1LQM6H889.yaml
```

## How to Run

For a list of parameters, [read the online documentation](https://tezos-reward-distributor-organization.github.io/tezos-reward-distributor/run.html), or run:

```bash
python3 src/main.py --help
```

The most common use case is to run in **mainnet** and start to make payments for the latest released rewards or continue making payments from the cycle after the last payment was done.

```bash
python3 src/main.py
```

TRD necessitates of an interface to get provided with income and delegator data in order to perform the needed calculations.

The default provider is the TzKT API. However, it is possible to change the data provider to a local node with the flag `-P rpc`.
In this case, the default node would be `127.0.0.1:8732`. In order to change the node URL for the provider, you can pass it in the form `node_url:port` using the flag `-A` (e.g. `-P rpc -A 127.0.0.1:8733`). Please note that the node should be an [archive node](https://tezos.gitlab.io/user/history_modes.html#setting-up-a-node-in-archive-mode), and that the port should be the RPC port specified while launching the node.

It is also possible to use a public RPC node with flag `-P prpc`, which defaults to `https://mainnet.smartpy.io`.

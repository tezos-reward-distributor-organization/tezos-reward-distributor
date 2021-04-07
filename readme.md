<img src="https://raw.githubusercontent.com/habanoz/trd-art/master/logo-narrow/trd_512__1.png" width="128" /> 

DISCLAIMER : TEZOS REWARD DISTRIBUTOR IS PROVIDED AS IS. IT IS UNDER CONSTANT DEVELOPMENT. EVENT THOUGH IT IS WELL TESTED, PLEASE USE IT WITH CARE. ALWAYS MAKE A PRE-RUN IN DRY MODE BEFORE MAKING ACTUAL PAYMENTS. IF YOU WANT TO RUN IN SERVICE MODE DO IT AFTER YOU ARE CONFIDENT WITH THE APPLICATION. IN SERVICE MODE ONLY UPDATE IF NEEDED.

PRIVACY : TEZOS REWARD DISTRIBUTOR COLLECTS ANONYMOUS STATISTICS. PLEASE READ OUR [STATISTICS POLICY](https://tezos-reward-distributor-organization.github.io/tezos-reward-distributor/statistics.html) FOR MORE INFORMATION.

## Tezos Reward Distributor : Run & Forget

[![Actions Status](https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/workflows/CI/badge.svg)](https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/actions)
[![Documentation Status](https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/workflows/Docs/badge.svg)](https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/actions)
[![Stable Documentation Status](https://img.shields.io/badge/docs-stable-blue.svg)](https://tezos-reward-distributor-organization.github.io/tezos-reward-distributor/)

TRD is a software for distributing staking rewards of delegators introduced in detail in this [Medium article](https://medium.com/@huseyinabanox/tezos-reward-distributor-e6588c4d27e7). This is not a script but a full scale application which can continuously run in the background as a Linux service. It can track cycles and make payments. However it does not have to be used as a service, but it can also be used interactively.
The documentation can be found [here](https://tezos-reward-distributor-organization.github.io/tezos-reward-distributor/).

TRD supports complex payments, pays in batches, and provides three back ends for calculations: Tezos RPC, [tzstats API](https://tzstats.com/) and [TzKT API](https://api.tzkt.io/). TRD is developed and tested extensively by the community.

**Provider notes:**

### TZStats

The [terms and conditions](https://tzstats.com/terms) of tzstats note that a license is needed for the commercial use of the API!

> If you wish to use the Data in a manner that is primarily intended for or directed towards commercial advantage or monetary compensation (such use, “Commercial Use”), KIDTSUNAMI requires that you enter into a separate commercial license agreement. Entering into a separate commercial license allows us to protect KIDTSUNAMI’s investment in the Data and to maintain the integrity of the Data.
>
> Please contact us at license@kidtsunami.com for more information about Commercial Uses of our Data.

### TzKt

With [#232](https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/pull/232) the backend of the Tezos Reward Distributor can be optionally [Powered by TzKT API](https://tzkt.io/) under the following terms:

> TzKT API is free for everyone and for both commercial and non-commercial usage.
>
> If your application or service uses the TzKT API in any forms: directly on frontend or indirectly on backend, you should mention that fact on your website or
> application by placing the label "Powered by TzKT API" with a direct link to tzkt.io.

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

To install required modules, use pip with requirements.txt provided.

```bash
cd tezos-reward-distributor
pip3 install -r requirements.txt
```

Regularly check and upgrade to the latest available version:

```bash
git fetch origin #fetches new branches
git status #see the changes
git pull
```

## Sample configuration

Before running the TRD, you need to configure it e.g by adding your staking address and payout process.
The configuration file should be included in the `~/pymnt/cfg/` directory by default. You can use the following command to copy and modify the example configuration:

```bash
# create directory
mkdir -p ~/pymnt/cfg/
cp tezos-reward-distributor/examples/tz1boot1pK9h2BVGXdyvfQSv8kd1LQM6H889.yaml ~/pymnt/cfg/
nano ~/pymnt/cfg/tz1boot1pK9h2BVGXdyvfQSv8kd1LQM6H889.yaml
```

## How to Run

For a list of parameters, run:

```bash
python3 src/main.py --help
```

The most common use case is to run in **mainnet** and start to make payments for the latest released rewards or continue making payments from the cycle after the last payment was done.

```bash
python3 src/main.py
```

TRD necessitates an interface to get provided with income and delegator data in order to perform the needed calculations.
The default provider is the public rpc node *mainnet.tezrpc.me*. However, it is possible to change the data provider with the flag -P rpc.
Please note that in this case, the default node would be localhost:8732. In order to change the node url for the provider, you can give the desired url 
under the flag -A followed with node_url:port (e.g. -P rpc -A 127.0.0.1:8733).
Please note that the node should be an archive node, and that the port should be the rpc port specified while launching the node.

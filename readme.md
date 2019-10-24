## Tezos Reward Distributor : Run & Forget [![Build Status](https://travis-ci.com/habanoz/tezos-reward-distributor.svg?branch=development)](https://travis-ci.com/habanoz/tezos-reward-distributor)

<img src="https://raw.githubusercontent.com/habanoz/trd-art/master/logo-narrow/trd_512__1.png" width="128" /> 

DISCLAIMER : TEZOS REWARD DISTRIBUTOR IS PROVIDED AS IS. IT IS UNDER CONSTANT DEVELOPMENT. EVENT THOUGH IT IS WELL TESTED, PLEASE USE WITH CARE. ALWAYS MAKE A PRE-RUN IN DRY MODE BEFORE MAKING ACTUAL PAYMENTS. IF YOU WANT TO RUN IN SERVICE MODE DO IT AFTER YOU ARE CONFIDENT WITH THE APPLICATION. IN SERVICE MODE DO NOT UPDATE OFTEN.

## Tezos Reward Distributor
TRD is a software for distributing baking rewards with delegators. The documentation can be found [here](https://habanoz.github.io/tezos-reward-distributor/). This is not a script but a full scale application which can run in the background all the time. It can track cycles and make payments. It does not have to be used as a service, It can also be used interactively.

TRD supports complex payments, pays in batches, provides two back ends for calculations: rpc and tzstats. Developed and tested extensively by the community. For more information please check following article.

https://medium.com/@huseyinabanox/tezos-reward-distributor-e6588c4d27e7

## TRD Art Work
https://github.com/habanoz/trd-art contains logo images. If you are using TRD and want to let everybody know about it, feel free to place them in your website.


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

Regularly check and upgrade to the latest available version:

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

### Funding

TRD is an open source project and will stay like this. It is not funded by any organization. A grant request is rejected by Tezos Foundation. However, I will try to continue to enhance the software and support the community.

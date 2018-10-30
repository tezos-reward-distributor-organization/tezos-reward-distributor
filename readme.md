A software for distributing baking rewards with delegators.

Design principals are: 

- Automatic Execution with no manual involvement : Run and forget
- Simplicity : Simple and intuitional parameter configuarion. Default values are ready for the most common use case. 
- Covering different use cases: supporters, special rates, future payments, security deposit owned by multiple parties, fee sharing among founders. Choose which cycle to pay and when to stop the application.
- Traceability: CSV payment reports with calculation details. Logs for traking application lifecycle.
- Testability: Dry for seeing results witout making any modification. Support for development networks e.g. zeronet, alphanet.
- Safety: Payment logs for avoiding multiple payments by mistake. Lock file for avoiding multiple instance running at the same time. Shutdown handlers for avoiding application shutdowns in the middle of a sensitive operation. 


Usage:

usage: main.py [-h] [-N {ZERONET,ALPHANET,MAINNET}] [-P PAYMENTS_DIR]
               [-T REPORTS_DIR] [-D] [-M {1,2,3}] [-C INITIAL_CYCLE]
               key

positional arguments:
  key                   tezos address or alias to make payments

optional arguments:
  -h, --help            show this help message and exit
  -N {ZERONET,ALPHANET,MAINNET}, --network {ZERONET,ALPHANET,MAINNET}
                        network name
  -P PAYMENTS_DIR, --payments_dir PAYMENTS_DIR
                        Directory to create payment logs
  -T REPORTS_DIR, --reports_dir REPORTS_DIR
                        Directory to create reports
  -D, --dry_run         Run without doing any payments. Suitable for testing.
                        Does not require locking.
  -M {1,2,3}, --run_mode {1,2,3}
                        Waiting decision after making pending payments. 1:
                        default option. Run forever. 2: Run all pending
                        payments and exit. 3: Run for one cycle and exit.
                        Suitable to use with -C option.
  -C INITIAL_CYCLE, --initial_cycle INITIAL_CYCLE
                        First cycle to start payment. For last released
                        rewards, set to 0. Non-positive values are interpreted
                        as : current cycle - abs(initial_cycle) -
                        (NB_FREEZE_CYCLE+1). If not set application will
                        continue from last payment made or last reward
                        released.
                        
How to Run:

Most common use case is run in mainnet and start make payments from last released rewards or continue making payments from the cycle last payment is done. Just provide the address/alias to make payments from. 

python main.py mytezospaymentaddress

Make payments for a single cycle:
python main.py -C 42 -M 3  mytezospaymentaddress

Make pending payments and stop:
python main.py -M 2  mytezospaymentaddress

Make pending payments beginning from a cycle and stop:
python main.py -C 30 -M 2 mytezospaymentaddress

Run in dry run mode in zeronet, make payments from cyle 30 and exit:
python main.py -D -N ZERONET -C 30 -M 3 mytezospaymentaddress


Bussiness Configuraion:

Bussiness configuration contains baker and delegator specific setting. Edit file BussinessConfiguration.py. Start by setting your baking address. Then set your delegation fee. If there are delegators with special rates, speciy them in specials_map. If your stake is owned by multiple parties speciy them in owners_map with ratios. If baker is run by multiple founders set them in founders_map.

Thats all.

Terms:

- Reward : Coins rewarded by the network for the baking/endorsing operations.
- Payment : Coins paid to delegators after excluding service fee.
- freeze cycle : number of cycles rewards are kept frozen by the tezos network. Can be given negative values to let the application make future payments.


 

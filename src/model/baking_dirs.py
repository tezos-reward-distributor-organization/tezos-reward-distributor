from util.dir_utils import (
    get_payment_root,
    get_calculations_root,
    get_successful_payments_dir,
    get_failed_payments_dir,
)
import os
from src.Constants import REPORTS_DIR, SIMULATIONS_DIR


# trd-data
# └──configurations
#    └── tz1xx.yaml
# └──simulations
#    └── tz1xxx
#       ├── calculations
#       │   └── 449.csv
#       └── payments
#           ├── done
#           │   └── 449.csv
#           └── failed
#               └── 449.csv
# └──reports
#    └── tz1xxx
#       ├── calculations
#       │   └── 449.csv
#       └── payments
#           ├── done
#           │   └── 449.csv
#           └── failed
#               └── 449.csv
class BakingDirs:
    def __init__(self, args, baking_address) -> None:
        super().__init__()

        # 7- get reporting directories
        if args.dry_run:
            reports_base = os.path.expanduser(args.reports_base + SIMULATIONS_DIR)
        else:
            reports_base = os.path.expanduser(args.reports_base + REPORTS_DIR)

        self.reports_dir = os.path.join(reports_base, baking_address)
        self.payments_root = get_payment_root(self.reports_dir, create=True)
        self.calculations_root = get_calculations_root(self.reports_dir, create=True)
        self.successful_payments_dir = get_successful_payments_dir(
            self.payments_root, create=True
        )
        self.failed_payments_dir = get_failed_payments_dir(
            self.payments_root, create=True
        )

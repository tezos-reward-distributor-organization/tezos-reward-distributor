from util.dir_utils import (
    get_payment_root,
    get_calculations_root,
    get_successful_payments_dir,
    get_failed_payments_dir,
)
import os
from Constants import REPORTS_DIR, SIMULATIONS_DIR

# Default folder structure:
#
# ~/pymnt/
# └──cfg
#    └── tz1xx.yaml
# └──logs
#    └── verbose_backup
#    │   └── app_verbose.gz
#    └── app.log
#    └── app_verbose.log
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

        # Get reporting directories
        if args.dry_run:
            base_directory = os.path.join(
                os.path.expanduser(os.path.normpath(args.base_directory)),
                SIMULATIONS_DIR,
                "",
            )

        else:
            base_directory = os.path.join(
                os.path.expanduser(os.path.normpath(args.base_directory)),
                REPORTS_DIR,
                "",
            )

        self.reports_dir = os.path.join(base_directory, baking_address, "")
        self.payments_root = get_payment_root(self.reports_dir, create=True)
        self.calculations_root = get_calculations_root(self.reports_dir, create=True)
        self.successful_payments_dir = get_successful_payments_dir(
            self.payments_root, create=True
        )
        self.failed_payments_dir = get_failed_payments_dir(
            self.payments_root, create=True
        )

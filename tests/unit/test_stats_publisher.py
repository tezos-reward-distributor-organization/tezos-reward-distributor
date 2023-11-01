import logging
from unittest import TestCase
from unittest.mock import patch, MagicMock

from stats.stats_publisher import stats_publisher
from uuid import uuid1

logger = logging.getLogger("unittesting")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


class TestStatsPublish(TestCase):
    @patch(
        "stats.stats_publisher.logger",
        MagicMock(
            debug=MagicMock(side_effect=print), info=MagicMock(side_effect=print)
        ),
    )
    def test_publish(self):
        stats_dict = {
            "uuid": str(uuid1()),
            "cycle": 1,
            "network": "ZERONET",
            "total_amount": 397,
            "nb_pay": 561,
            "nb_failed": 561,
            "nb_unknown": 0,
            "total_attmpts": 3,
            "nb_founders": 0,
            "nb_owners": 0,
            "nb_merged": 2,
            "nb_delegators": 559,
            "pay_xfer_fee": 1,
            "pay_ra_fee": 1,
            "trdver": "8.0",
            "m_run": 0,
            "m_prov": "prpc",
            "m_relov": 0,
            "m_offset": 16,
            "m_docker": 0,
            "pythonver": "3.6",
            "os": "Linux-3.10.0-957.12.2.el7.x86_64-x86_64-with-centos-7.7.1908-Core",
        }

        try:
            stats_publisher(stats_dict)
        except Exception:
            print("FAIL")

from tzkt.tzkt_api import TzKTApi, TzKTApiError
from api.block_api import BlockApi
from log_config import main_logger

logger = main_logger.getChild("tzkt_block_api")


class TzKTBlockApiImpl(BlockApi):

    def __init__(self, nw, base_url=None):
        super(TzKTBlockApiImpl, self).__init__(nw)
        if base_url is None:
            self.api = TzKTApi.from_network(nw['NAME'])
        else:
            self.api = TzKTApi.from_url(base_url)

    def get_current_level(self) -> int:
        """
        Get head level
        :returns: 0
        """
        head = self.api.get_head()
        if not head.get('synced'):
            raise TzKTApiError('Not synced')

        return int(head['level'])

    def get_revelation(self, pkh, verbose=False):
        account = self.api.get_account_by_address(pkh)
        return bool(account["revealed"])

    def get_delegatable(self, pkh):
        account = self.api.get_account_by_address(pkh)
        return account["type"] == "delegate" and bool(account["active"])

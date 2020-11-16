from tzkt.tzkt_api import TzKTApi, TzKTApiError
from api.block_api import BlockApi


class TzKTBlockApiImpl(BlockApi):

    def __init__(self, nw, base_url=None):
        super(TzKTBlockApiImpl, self).__init__(nw)
        if base_url is None:
            self.api = TzKTApi.from_network(nw['NAME'].lower())
        else:
            self.api = TzKTApi.from_url(base_url)

    def get_current_level(self) -> int:
        """
        Get head level
        :returns: 0
        """
        head = self.api.get_head()
        if not head.get('synced'):
            raise TzKTApiError(f'Not synced')

        return int(head['level'])

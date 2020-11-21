from tzkt.tzkt_api import TzKTApi, TzKTApiError
from api.block_api import BlockApi


class TzKTBlockApiImpl(BlockApi):

    def __init__(self, nw, verbose=False, base_url=None):
        super(TzKTBlockApiImpl, self).__init__(nw)
        if base_url is None:
            self.api = TzKTApi.from_network(nw['NAME'].lower(), verbose=verbose)
        else:
            self.api = TzKTApi.from_url(base_url, verbose=verbose)

    def get_current_level(self, verbose=False) -> int:
        """
        Get head level
        :param verbose: not used
        :returns: 0
        """
        head = self.api.get_head()
        if not head.get('synced'):
            raise TzKTApiError('Not synced')

        return int(head['level'])

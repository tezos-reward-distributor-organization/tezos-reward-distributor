from tzkt.tzkt_api import TzKTApi, TzKTApiError
from api.block_api import BlockApi


class TzKTBlockApiImpl(BlockApi):

    def __init__(self, nw, verbose=False):
        super(TzKTBlockApiImpl, self).__init__(nw)
        self.api = TzKTApi.from_network(nw['NAME'].lower(), verbose=verbose)

    def get_current_level(self, verbose=False) -> int:
        """
        Get head level
        :param verbose: not used
        :returns: 0
        """
        head = self.api.get_head()
        if not head.get('synced'):
            raise TzKTApiError(f'Not synced')

        return int(head['level'])

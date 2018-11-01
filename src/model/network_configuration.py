class NetworkConfiguration():
    def __init__(self, preserved_cycles, time_between_blocks, blocks_per_cycle):
        super(NetworkConfiguration, self).__init__()
        self.preserved_cycles = preserved_cycles
        self.time_between_blocks = time_between_blocks
        self.blocks_per_cycle = blocks_per_cycle

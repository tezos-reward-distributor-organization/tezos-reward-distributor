from model.reward_log import TYPE_FOUNDERS_PARENT, TYPE_OWNERS_PARENT


class ServiceFeeCalculator:
    def __init__(self, supporters_set, specials_map, standard_fee):
        self.supporters_set = supporters_set
        self.specials_map = {}

        self.standard_fee = standard_fee / 100.0

        for addr, ratio in specials_map.items():
            self.specials_map[addr] = ratio / 100.0

    def calculate(self, address):
        service_fee = self.standard_fee

        if address in self.supporters_set or address in [
            TYPE_FOUNDERS_PARENT,
            TYPE_OWNERS_PARENT,
        ]:
            service_fee = 0.0
        elif address in self.specials_map:
            service_fee = self.specials_map[address]

        return service_fee

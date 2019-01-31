from model.payment_log import PaymentRecord
from util.num_utils import floorf


class PaymentCalculator:
    def __init__(self, founders_map, owners_map, reward_list, total_rewards, service_fee_calculator, cycle):
        self.owners_map = owners_map
        self.total_rewards = total_rewards
        self.cycle = cycle
        self.fee_calc = service_fee_calculator
        self.reward_list = reward_list
        self.founders_map = founders_map

    #
    # calculation details
    #
    # total reward = delegators reward + owners reward = delegators payment + delegators fee + owners payment
    # delegators reward = delegators payment + delegators fee
    # owners reward = owners payment = total reward - delegators reward
    # founders reward = delegators fee = total reward - delegators reward
    ####
    def calculate(self):
        pymnts = []

        # 1- calculate delegators payments
        delegators_total_pymnt = 0
        delegators_total_ratio = 0
        delegators_total_fee = 0
        for ri in self.reward_list:
            # set fee rate
            fee_rate = self.fee_calc.calculate(ri.address)
            pymnt_amnt = floorf(ri.reward * (1 - fee_rate), 3)

            # this indicates, service fee is very low (e.g. 0) and pymnt_amnt is rounded up
            if pymnt_amnt - ri.reward > 0:
                pymnt_amnt = ri.reward

            fee = (ri.reward - pymnt_amnt)

            pr = PaymentRecord.DelegatorInstance(self.cycle, ri.address, ri.ratio, fee_rate, ri.reward, fee, pymnt_amnt)
            pymnts.append(pr)

            delegators_total_pymnt = delegators_total_pymnt + pymnt_amnt
            delegators_total_ratio = delegators_total_ratio + ri.ratio
            delegators_total_fee = delegators_total_fee + fee

        # 2- calculate deposit owners payments. They share the remaining rewards according to their ratio (check config)
        owners_total_pymnt = 0
        owners_total_reward = self.total_rewards - (delegators_total_pymnt + delegators_total_fee)
        no_owners = True
        
        # Skip if no owners defined
        if len(self.owners_map) > 0:
            no_owners = False
            for address, ratio in self.owners_map.items():
                owner_pymnt_amnt = floorf(ratio * owners_total_reward, 3)
                owners_total_pymnt = owners_total_pymnt + owner_pymnt_amnt
                pymnts.append(PaymentRecord.OwnerInstance(self.cycle, address, ratio, owner_pymnt_amnt, owner_pymnt_amnt))

        # move remaining rewards to service fee bucket
        # 3- service fee is shared among founders according to founders_map ratios
        founders_total_pymnt = 0
        founders_total_reward = self.total_rewards - delegators_total_pymnt - owners_total_pymnt
        no_founders = True

        # If no owners paid, must include their would-be reward in this calculation
        if no_owners:
            founders_total_reward = founders_total_reward - owners_total_reward
        
        # Skip if no founders defined
        if len(self.founders_map) > 0:
            no_founders = False
            for address, ratio in self.founders_map.items():
                founder_pymnt_amnt = floorf(ratio * founders_total_reward, 6)
                pymnts.append(PaymentRecord.FounderInstance(self.cycle, address, ratio, founder_pymnt_amnt))

        ###
        # sanity check
        #####
        total_sum = 0
        for payment_log in pymnts:
            total_sum = total_sum + payment_log.payment

        # if no owners/no founders, add that would-be amount to total_sum
        # the baker will keep (owners_total_reward + founders_total_reward) automatically when unfrozen
        if no_owners:
            total_sum = total_sum + owners_total_reward
        if no_founders:
            total_sum = total_sum + founders_total_reward

        # if there is a minor difference due to floor function; it is added to last payment
        if self.total_rewards - total_sum > 1e-6:
            last_pymnt_log = pymnts[-1]  # last payment, probably one of the founders
            last_pymnt_log.payment = last_pymnt_log.payment + (self.total_rewards - total_sum)

        # this must never return true
        if abs(total_sum - self.total_rewards) > 5e-6:
            raise Exception("Calculated reward {} is not equal to total reward {}".format(total_sum, self.total_rewards))

        return pymnts

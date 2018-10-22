class PaymentCalculator:
    def __init__(self, founders_map, owners_map, reward_list, total_rewards, service_fee_calculator, cycle):
        self.owners_map = owners_map
        self.total_rewards = total_rewards
        self.cycle = cycle
        self.fee_calc = service_fee_calculator
        self.reward_list = reward_list
        self.founders_map = founders_map
        self.total_service_fee = 0

    def calculate(self):
        payments = []

        # calculate delegators payments
        delegators_total_pymnt = 0
        delegators_total_ratio = 0
        delegators_total_fee = 0
        for reward_item in self.reward_list:
            reward = reward_item['reward']
            ktAddress = reward_item['address']
            ratio = reward_item['ratio']

            pymnt_amnt = round(reward * (1 - self.fee_calc.calculate(ktAddress)), 3)


            # this indicates, service fee is very low (e.g. 0) and pymnt_amnt is rounded up
            if pymnt_amnt-reward > 0:
                pymnt_amnt=reward

            fee = (reward - pymnt_amnt)

            print("pa {} r {} rate {} fee {}".format(pymnt_amnt, reward, (1 - self.fee_calc.calculate(ktAddress)),fee))

            payments.append({'payment': pymnt_amnt, 'fee': fee, 'address': ktAddress, 'cycle': self.cycle,'type':'D'})

            delegators_total_pymnt = delegators_total_pymnt + pymnt_amnt
            delegators_total_ratio = delegators_total_ratio + ratio
            delegators_total_fee = delegators_total_fee + fee

        # calculate deposit owners payments
        owners_ratio = 1 - delegators_total_ratio
        owners_total_payment = 0
        owners_total_reward = self.total_rewards - delegators_total_fee
        for address, ratio in self.owners_map.items():
            owner_pymnt_amnt = round((owners_ratio * ratio) * owners_total_reward, 3)
            owners_total_payment = owners_total_payment + owner_pymnt_amnt

            payments.append({'payment': owner_pymnt_amnt, 'fee': 0, 'address': address, 'cycle': self.cycle,'type':'O'})
            print("pa {} r {} rate {} fee {}".format(pymnt_amnt, reward, (1 - self.fee_calc.calculate(ktAddress)), fee))

        # move remaining rewards to service fee bucket
        self.total_service_fee = self.total_rewards - delegators_total_pymnt - owners_total_payment

        # service fee is shared among founders according to founders_map ratios
        for address, ratio in self.founders_map.items():
            pymnt_amnt = ratio * self.total_service_fee

            payments.append({'payment': pymnt_amnt, 'fee': 0, 'address': address, 'cycle': self.cycle, 'type': 'F'})

        total_sum=0
        for payment in payments:
            total_sum=total_sum+payment['payment'] +payment['fee']
            print("pa {} fee {} ".format(payment['payment'], payment['fee']))
        raise Exception("calculated reward {} is grater than total reward {}".format(total_sum,self.total_rewards))
        return payments

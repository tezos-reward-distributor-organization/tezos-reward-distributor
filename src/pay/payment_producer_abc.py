from abc import ABC, abstractmethod


class PaymentProducerABC(ABC):
    def __init__(self):
        super(PaymentProducerABC, self).__init__()

    @abstractmethod
    def on_success(self, pymnt_batch):
        pass

    @abstractmethod
    def on_fail(self, pymnt_batch):
        pass
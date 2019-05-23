class PaymentBatch:
    def __init__(self, producer_ref, cycle, batch) -> None:
        super().__init__()
        self.producer_ref = producer_ref
        self.cycle = cycle
        self.batch = batch

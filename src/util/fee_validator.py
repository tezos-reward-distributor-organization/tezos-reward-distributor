class FeeValidator:

    def __init__(self, specifier) -> None:
        super().__init__()
        self.specifier=specifier

    def validate(self, fee):
        if fee < 0:
            raise Exception("Fee for {} cannot be less than 0, it is {}".format(self.specifier, fee))

        if fee > 1:
            raise Exception("Fee for {} cannot be greater than 1, it is {}".format(self.specifier, fee))

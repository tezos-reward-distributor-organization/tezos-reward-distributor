class FeeValidator:

    def __init__(self, specifier) -> None:
        super().__init__()
        self.specifier = specifier

    def validate(self, fee):
        failed=False
        try:
            if fee != 0 and not 1 <= fee <= 100:
                failed=True
        except TypeError:
            failed=True

        if failed:
            raise Exception("Fee for {} cannot be {}. Valid values are 0, [1-100]".format(self.specifier, fee))
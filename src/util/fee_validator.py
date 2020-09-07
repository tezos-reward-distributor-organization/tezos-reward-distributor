class FeeValidator:

    def __init__(self, specifier) -> None:
        super().__init__()
        self.specifier = specifier

    def validate(self, fee):
        failed = False
        try:
            if not 0 <= fee <= 100:
                failed = True
        except TypeError:
            failed = True

        if failed:
            raise Exception("Fee for {} cannot be {}. Valid range is [0-100]".format(self.specifier, fee))

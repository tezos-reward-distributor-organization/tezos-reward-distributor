PKH_LENGHT = 36


class BaseError(Exception):
    pass


class IncorrectAddressError(BaseError):
    pass


class IncorrectLengthError(BaseError):
    pass


class AddressValidator:
    def __init__(self, context) -> None:
        super().__init__()
        self.context = context

    def validate(self, address):
        if not address.startswith("tz") and not address.startswith("KT"):
            raise IncorrectAddressError(
                "Incorrect input in {}, '{}' is not a tz or KT address".format(
                    self.context, address
                )
            )

        if len(address) != PKH_LENGHT:
            raise IncorrectLengthError(
                "Incorrect input in {}, '{}' length must be {}".format(
                    self.context, address, PKH_LENGHT
                )
            )

    @staticmethod
    def isaddress(address):
        if len(address) == PKH_LENGHT:
            if address.startswith("tz") or address.startswith("KT"):
                return True

        return False

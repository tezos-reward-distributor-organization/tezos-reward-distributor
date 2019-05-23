PKH_LENGHT = 36


class AddressValidator:

    def __init__(self, context) -> None:
        super().__init__()
        self.context = context

    def validate(self, address):
        if len(address) == PKH_LENGHT:
            if not address.startswith("tz") and not address.startswith("KT"):
                raise Exception("Incorrect input in {}, {} is Not a tz or KT address".format(self.context, address))
        else:
            raise Exception(
                "Incorrect input in {}, address({}) length must be {}".format(self.context, address, PKH_LENGHT))

    @staticmethod
    def isaddress(address):
        if len(address) == PKH_LENGHT:
            if address.startswith("tz") or address.startswith("KT"):
                return True

        return False

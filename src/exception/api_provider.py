# API providers should throw this exception when an
# error condition happens while fetching data from source
#
# API providers may subclass for their specific needs
#


class ApiProviderException(Exception):
    pass

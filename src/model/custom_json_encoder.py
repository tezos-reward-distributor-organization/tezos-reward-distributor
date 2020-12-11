import json

from config.addr_type import AddrType
from Constants import RewardsType


class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, AddrType):
            return AddrType.to_string(obj)
        if isinstance(obj, RewardsType):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

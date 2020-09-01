from enum import Enum


class AddrType(Enum):
    KT = 1
    TZ = 2
    KTALS = 3
    TZALS = 4,

    @staticmethod
    def to_string(obj):
        self = obj
        if self.value == 1:
            return 'KT'
        if self.value == 2:
            return 'TZ'
        if self.value == 3:
            return 'KTALS'
        if self.value == 4:
            return 'TZALS'

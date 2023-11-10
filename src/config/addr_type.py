from enum import Enum


class AddrType(Enum):
    KT = 1
    TZ = 2
    KTALS = 3
    TZALS = 4

    def is_kt(self):
        return self.value == 1

    def is_tz(self):
        return self.value == 2

    def is_ktals(self):
        return self.value == 3

    def is_tzals(self):
        return self.value == 4

    @staticmethod
    def to_string(obj):
        self = obj
        if self.value == 1:
            return "KT"
        if self.value == 2:
            return "TZ"
        if self.value == 3:
            return "KTALS"
        if self.value == 4:
            return "TZALS"

    def __str__(self):
        return self.name

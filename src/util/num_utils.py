from math import ceil, floor


def ceilf(num, ndigits):
    return ceil(num * 10**ndigits) / 10**ndigits


def floorf(num, ndigits):
    return floor(num * 10**ndigits) / 10**ndigits

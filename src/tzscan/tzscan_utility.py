import random


def rand_mirror():
    mirror = random.randint(1, 6)

    if mirror == 2:
        mirror = 3

    return mirror

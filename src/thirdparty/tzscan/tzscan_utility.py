import random


def rand_mirror():
    mirror = random.randint(1, 6)

    # mirror 4 not working
    if mirror == 4:
        mirror = 3
    if mirror == 6:
        mirror = 3

    return mirror

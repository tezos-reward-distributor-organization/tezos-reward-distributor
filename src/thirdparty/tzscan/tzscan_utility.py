import random


def rand_mirror():
    mirror = random.randint(1, 6)

    # mirror 4 not working
    if mirror == 4:
        mirror = 2
    if mirror == 6:
        mirror = 2
    if mirror == 3:
        mirror = 2

    return mirror

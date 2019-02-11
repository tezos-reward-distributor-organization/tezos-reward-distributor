# baker's extende bussiness parameters

# set of delegators to exclude from reward calculations, total reward is shared among remaining delegators
excluded_delegators_set={"KT1VYLbR7Cp4xxywWR4c12BPbkmrqSf5UXad"}

# number of digits after decimal point, e.g. 3.231 has scale 3 while 0.12 has scale of 2.
# Setting scale of 3.238 to 2 will result in rounding down to 3.23
# set None to disable rounding
# Note that : Always rounded down to avoid excess payments
pymnt_scale = 3

# number of digits after a decimal point in a percentage value
# e.g. 23.4% = 0.234 has scale 3 while 12.345% = 0.12345 has scale of 5.
# Setting scale of 0.238 to 2 will result is rounded to the nearest number : 0.24
# set None to disable rounding
prcnt_scale = 5
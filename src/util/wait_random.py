from random import randint
from time import sleep
from log_config import main_logger


def wait_random(block_time):
    slp_tm = randint(block_time // 2, block_time)
    main_logger.debug("Wait for {} seconds before trying again".format(slp_tm))
    sleep(slp_tm)

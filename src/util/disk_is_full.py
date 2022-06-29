import shutil
from log_config import main_logger
from Constants import DISK_LIMIT_PERCENTAGE, GIGA_BYTE, DISK_LIMIT_SIZE

logger = main_logger


def disk_is_full(path="/"):
    total, _, free = shutil.disk_usage(path)
    free_percentage = free / total
    if free_percentage < DISK_LIMIT_PERCENTAGE and free < DISK_LIMIT_SIZE:
        # Return true if the system has less then 10% free disk space
        logger.critical(
            "Disk is becoming full. Only {0:.2f} Gb left from {1:.2f} Gb. Please clean up disk to continue saving logs and reports.".format(
                free / GIGA_BYTE, total / GIGA_BYTE
            )
        )
        return True
    return False

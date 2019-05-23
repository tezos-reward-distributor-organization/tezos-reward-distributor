import logging

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(threadName)-9s %(message)s', )

main_logger = logging.getLogger('main')
main_logger.setLevel(logging.DEBUG)

# create file handler which logs even debug messages
fh = logging.FileHandler('app.log')
fh.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter and add it to the handlers
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(threadName)-9s - %(message)s')
formatter = logging.Formatter('%(asctime)s - %(threadName)-9s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# add the handlers to logger
main_logger.addHandler(ch)
main_logger.addHandler(fh)
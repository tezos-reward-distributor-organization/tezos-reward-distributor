import os
import sqlite3
import json
from log_config import main_logger
from model.baking_conf import BakingConfJsonEncoder

logger = main_logger


class ConfigStorage:

    def __init__(self, _storage):

        logger.info("ConfigStorage - Init")

        self._storage = _storage

        sqlite3.register_adapter(dict, adapt_json)
        sqlite3.register_adapter(set, adapt_json)
        sqlite3.register_adapter(list, adapt_json)
        sqlite3.register_converter("BLOB", convert_json)

        self.__create_tables()

    def get_baker_config(self):
        j_config = None
        with self._storage as dbh:
            try:
                r_sql = "SELECT bakerConfig FROM config LIMIT 1"
                cur = dbh.execute(r_sql)
                row = cur.fetchone()
                if row is None or len(row) != 1:
                    return None
                j_config = row[0]
            except sqlite3.Error as e:
                raise ConfigStorageException("Unable to get baker config from DB: {}".format(e)) from e
            except ConfigStorageException:
                raise

        return j_config

    def save_baker_config(self, baker_addr, baker_cfg_dict):

        i_sql = "REPLACE INTO config (bakerAddr, bakerConfig) VALUES (?, ?)"

        with self._storage as dbh:
            try:
                dbh.execute(i_sql, (baker_addr, baker_cfg_dict))
            except sqlite3.Error as e:
                raise ConfigStorageException("Unable to save baker config to database: {}".format(e)) from e
            except:
                raise

    def __create_tables(self):

        with self._storage as dbh:
            try:
                dbh.execute("CREATE TABLE IF NOT EXISTS config (bakerAddr TEXT PRIMARY KEY, bakerConfig BLOB)")

            except sqlite3.Error as e:
                raise ConfigStorageException("Unable to create tables: {}".format(e)) from e
            except:
                raise

# SQLite-JSON helpers
def adapt_json(data):
    return (json.dumps(data, cls=BakingConfJsonEncoder)).encode()

def convert_json(blob):
    return json.loads(blob.decode())

class ConfigStorageException(Exception):
    pass

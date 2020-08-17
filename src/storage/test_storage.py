from unittest import TestCase
from sqlite3 import OperationalError
from storage.storage import Storage
from tempfile import TemporaryDirectory


class TestStorage(TestCase):

    def test_sqlite(self):
        tempDir = TemporaryDirectory()
        with tempDir as t:

            # Verify that SQLite3 library can open a DB
            s = Storage(t, False)

            # Run query
            with s as dbh:
                dbh.execute("CREATE TABLE testing (id INTEGER PRIMARY KEY)")

                # Run bad query
                with self.assertRaises(OperationalError):
                    dbh.execute("INSERT INTO testing (id, name) VALUES (NULL, 'John')")

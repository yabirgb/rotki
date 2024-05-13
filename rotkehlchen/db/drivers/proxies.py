from multiprocessing.managers import BaseManager
import sqlite3


class SQLiteManager(BaseManager):
    def __init__(self):
        super().__init__()
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()

    def execute(self, query):
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def executemany(self, query, params):
        self.cursor.executemany(query, params)
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()
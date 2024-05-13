from contextlib import contextmanager
from multiprocessing.managers import BaseManager, BaseProxy, SyncManager
from multiprocessing import Lock
import sqlite3


# Manager server class.
class SQLiteManager(SyncManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn = sqlite3.connect('/tmp/test.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.execute_lock = Lock()

    def execute(self, query, bindings=()):
        self.cursor.execute(query, bindings)
        return self.cursor.fetchall()

    def executemany(self, query, params):
        self.cursor.executemany(query, params)
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()

    def get_conn(self):
        return self.conn

    def get_lock(self):
        return self.execute_lock

if __name__ == '__main__':
    # Creates and run a server instance.
    server = SQLiteManager(address=('', 50000), authkey=b"123")
    server.register('execute', server.execute)
    server.register('get_conn', server.get_conn)
    server.register('get_lock', server.get_lock)
    import threading
    print(threading.get_native_id())

    cur = server.conn.cursor() 
    cur.execute('CREATE TABLE IF NOT EXISTS test_table(value INTEGER)')

    server.get_server().serve_forever()
    print('yoz')
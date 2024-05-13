from contextlib import contextmanager
from multiprocessing.managers import BaseManager
import time

# Manager
class Client(BaseManager):
    
    @contextmanager
    def write_cursor(self):
        self.get_lock().acquire()
        try:
            self.execute('BEGIN TRANSACTION')
            yield
        except Exception as e:
            print(f'ERROR {e}')
            self.get_conn().rollback()
        else:
            self.get_conn().commit()
        finally:
            self.get_lock().release()


Client.register('execute')
Client.register('get_conn')
Client.register('get_lock')
    

if __name__ == '__main__':
    import threading
    print(threading.get_native_id())

    client = Client(address=('', 50000), authkey=b"123")
    client.connect()
    import random

    while True:
        print('pre enter')
        with client.write_cursor():
            print(client.execute('INSERT INTO test_table(value) VALUES (?) RETURNING value', (random.randint(0, 100),)))
            print(client.execute('SELECT COUNT(*) FROM test_table'))
            print('----')
            time.sleep(10)
        print('exited')
        # time.sleep(random.random())
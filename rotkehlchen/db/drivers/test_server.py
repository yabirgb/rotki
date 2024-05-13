import multiprocessing
import sqlite3
from multiprocessing.managers import BaseManager, BaseProxy

class Server(multiprocessing.Process):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port

    def run(self):
        # Create a BaseManager
        manager = BaseManager(address=(self.host, self.port))
        manager.start()

        # Define the execute method
        def execute(sql):
            conn = sqlite3.connect(':memory:')
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
            result = cursor.fetchall()
            conn.close()
            return result

        # Define the executemany method
        def executemany(sql, params):
            conn = sqlite3.connect(':memory:')
            cursor = conn.cursor()
            cursor.executemany(sql, params)
            conn.commit()
            result = cursor.fetchall()
            conn.close()
            return result

        # Register the execute and executemany methods
        manager.register('execute', execute)
        manager.register('executemany', executemany)

        print(f"Server listening on {self.host}:{self.port}")

        while True:
            conn = manager.connect()
            while True:
                try:
                    cmd = conn.recv()
                    if cmd == 'quit':
                        break
                    elif cmd == 'execute':
                        sql = conn.recv()
                        result = execute(sql)
                        conn.sendall(str(result).encode())
                    elif cmd == 'executemany':
                        sql = conn.recv()
                        params = conn.recv()
                        results = executemany(sql, params)
                        conn.sendall(str(results).encode())
                except EOFError:
                    break
            conn.close()

if __name__ == "__main__":
    # Create a server process
    server = Server("localhost", 8080)
    server.start()

    # Wait for the process to finish
    server.join()
import multiprocessing
from multiprocessing.managers import BaseManager

class Client(multiprocessing.Process):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port

    def run(self):
        # Create a BaseManager
        manager = BaseManager(address=(self.host, self.port))
        manager.connect()

        # Execute a query
        result = manager.execute('SELECT * FROM table_name')
        print(result)

        # Execute a query with multiple parameters
        params = [(1, 2), (3, 4)]
        results = manager.executemany('INSERT INTO table_name VALUES (?, ?)', params)
        print(results)

if __name__ == "__main__":
    # Create a client process
    client = Client("localhost", 8080)
    client.start()

    # Wait for the process to finish
    client.join()
import multiprocessing
from multiprocessing.connection import Listener, Client
import time

class Server(multiprocessing.Process):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port

    def run(self):
        # Create a listener
        listener = Listener((self.host, self.port))

        print(f"Server listening on {self.host}:{self.port}")

        while True:
            with listener.accept() as conn:
                print(f"Connected by {conn.__dict__}")
                while True:
                    try:
                        data = conn.recv()
                        if not data:
                            break
                        print(f"Received: {data.decode()}")
                        conn.send(data)
                    except EOFError:
                        break

class ClientServer(multiprocessing.Process):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port

    def run(self):
        # Create a client
        conn = Client((self.host, self.port))

        print(f"Connected to {self.host}:{self.port}")

        while True:
            data = 'HELLO WORLD'
            conn.send(data.encode())
            print(f"Sent: {data}")
            data = conn.recv()
            print(f"Received: {data.decode()}")
            if data.decode() == "quit":
                break
        conn.close()

if __name__ == "__main__":
    # Create a server process
    server = Server('127.0.0.1', 3100)
    server.start()

    # Create a client process
    client = ClientServer('127.0.0.1', 3100)
    client.start()

    # Wait for the processes to finish
    server.join()
    client.join()
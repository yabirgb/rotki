import multiprocessing
import socket


class Server(multiprocessing.Process):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port

    def run(self):
        # Create a socket object
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.host, self.port))
        sock.listen(1)

        print(f"Server listening on {self.host}:{self.port}")

        while True:
            conn, addr = sock.accept()
            print(f"Connected by {addr}")
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                print(f"Received: {data.decode()}")
                conn.sendall(data)
            conn.close()

class Client(multiprocessing.Process):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port

    def run(self):
        # Create a socket object
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))

        print(f"Connected to {self.host}:{self.port}")

        while True:
            data = 'HELLO'
            sock.sendall(data.encode())
            print(f"Sent: {data}")
            data = sock.recv(1024)
            print(f"Received: {data.decode()}")
            if data.decode() == "quit":
                break
        sock.close()

if __name__ == "__main__":
    # Create a server process
    server = Server("localhost", 8080)
    server.start()

    # Create a client process
    client = Client("localhost", 8080)
    client.start()

    # Wait for the processes to finish
    server.join()
    client.join()
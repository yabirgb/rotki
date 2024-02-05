"""
ZMQ with Threaded Workers on Python 3

Python 3 compatible port of: https://gist.github.com/felipecruz/883983
"""

import zmq
from random import choice
import asyncio
import zmq.asyncio



class ClientTask:
    """ClientTask"""

    async def run(self):
        ctx = zmq.asyncio.Context()
        socket = ctx.socket(zmq.XREQ)
        identity = 'worker-%d' % (choice([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
        socket.setsockopt(zmq.IDENTITY, identity.encode('utf-8'))
        socket.connect('tcp://localhost:5570')
        print('Client %s started' % (identity))
        poller = zmq.asyncio.Poller()
        poller.register(socket, zmq.POLLIN)
        reqs = 0
        while True:
            for i in range(5):
                sockets = dict(await poller.poll(1000))
                if socket in sockets:
                    if sockets[socket] == zmq.POLLIN:
                        msg = await socket.recv()
                        print('%s: %s\n' % (identity, msg))
                        del msg
            reqs = reqs + 1
            print('Req #%d sent..' % (reqs))
            socket.send(b'request #%d' % (reqs))

        socket.close()
        context.term()


class ServerTask:
    """ServerTask"""

    async def run(self):
        context = zmq.asyncio.Context()
        frontend = context.socket(zmq.DEALER)
        frontend.bind('tcp://*:5570')

        backend = context.socket(zmq.XREQ)
        backend.bind('inproc://backend')

        workers = []
        loop = asyncio.get_running_loop()
        for _ in range(5):
            worker = ServerWorker(context)
            loop.create_task(worker.run())
            workers.append(worker)

        poll = zmq.Poller()
        poll.register(frontend, zmq.POLLIN)
        poll.register(backend, zmq.POLLIN)
        print('Server started')
        while True:
            sockets = dict(poll.poll())
            if frontend in sockets:
                if sockets[frontend] == zmq.POLLIN:
                    msg = await frontend.recv()
                    print('Server received %s' % (msg))
                    await backend.send(msg)
            if backend in sockets:
                if sockets[backend] == zmq.POLLIN:
                    msg = await backend.recv()
                    await frontend.send(msg)


        frontend.close()
        backend.close()
        context.term()


class ServerWorker:
    """ServerWorker"""

    def __init__(self, context: zmq.asyncio.Context):
        self.context = context

    async def run(self):
        worker = self.context.socket(zmq.XREQ)
        worker.connect('inproc://backend')
        print('Worker started')
        while True:
            msg = worker.recv()
            print('Worker received %s' % (msg))
            replies = choice(range(5))
            for _ in range(replies):
                await worker.send(msg)
            del msg

        worker.close()

def main():
    """main function"""
    import sys
    if sys.argv[1] == 's':
        server = ServerTask()
        asyncio.run(server.run())
    else:
        client = ClientTask()
        asyncio.run(client.run())

if __name__ == '__main__':
    main()

import asyncio
import json
import sqlite3
import sys
from typing import Any
import aiosqlite

import concurrent.futures

import zmq
from zmq.asyncio import Context, Poller

FRONTEND_ADDR = 'tcp://*:5570'
#FRONTEND_ADDR = 'inproc://frontend'
BACKEND_ADDR = 'inproc://backend'

class Server:
    """A server to set up and initialize clients and request handlers"""

    def __init__(self, loop: asyncio.BaseEventLoop, context: Context):
        self.loop = loop
        self.context = context

        self.connection = sqlite3.connect('rotkehlchen/data/global.db', check_same_thread=False)

    def run_server(self):
        tasks = []
        frontend = self.context.socket(zmq.ROUTER)
        frontend.bind(FRONTEND_ADDR)
        backend = self.context.socket(zmq.DEALER)
        backend.bind(BACKEND_ADDR)
        task = run_proxy(frontend, backend)
        tasks.append(task)

        for idx in range(5):
            worker = Worker(self.context, idx, self.connection, self.loop)
            task = asyncio.Task(worker.run_worker())
            tasks.append(task)

        return tasks


class Worker:
    """A request handler"""

    def __init__(self, context: Context, idx: int, connection: sqlite3.Connection, loop: asyncio.BaseEventLoop):
        self.context = context
        self.idx = idx
        self.connection = connection
        self.loop = loop
        self.pool = concurrent.futures.ThreadPoolExecutor()

    def query(self, query: str, bindings: list[Any]) -> list[Any]:
        cursor = self.connection.cursor()
        output = cursor.execute(query, bindings).fetchall()
        cursor.close()
        return output

    async def run_worker(self):
        worker = self.context.socket(zmq.DEALER)
        worker.connect(BACKEND_ADDR)
        print(f'Worker {self.idx} started')
        while True:
            response = await worker.recv_multipart()
            ident, msg = response
            print(f'Worker {self.idx} received {msg} from {ident.hex()}')
            data = json.loads(msg)
            output = await self.loop.run_in_executor(self.pool, self.query, data['query'], data['bindings'])
            await worker.send_multipart([ident, json.dumps({'response': output}).encode()])


async def run_proxy(socket_from: zmq.Socket, socket_to: zmq.Socket):
    poller = Poller()
    poller.register(socket_from, zmq.POLLIN)
    poller.register(socket_to, zmq.POLLIN)
    while True:
        events = await poller.poll()
        events = dict(events)
        if socket_from in events:
            msg = await socket_from.recv_multipart()
            await socket_to.send_multipart(msg)
        elif socket_to in events:
            msg = await socket_to.recv_multipart()
            await socket_from.send_multipart(msg)


def run(loop: asyncio.BaseEventLoop):
    context = Context()
    server = Server(loop, context)
    tasks = server.run_server()
    loop.run_until_complete(asyncio.gather(*tasks))


def main():
    """main function"""
    print('(main) starting')
    try:
        loop = asyncio.get_event_loop()
        run(loop)
    except KeyboardInterrupt:
        print('\nFinished (interrupted)')

if __name__ == '__main__':
    main()

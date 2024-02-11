import json
import logging
from typing import Any
import zmq.green as zmq
import aiosqlite

from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class MountainsDB:

    def __init__(self):
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.XREQ)
        self.identity = 'worker-rotki'
        self.socket.setsockopt(zmq.IDENTITY, self.identity.encode('utf-8'))
        self.socket.connect('tcp://localhost:5570')
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        log.info(f'Client {self.identity} started')

    def execute(self, query: str, bindings: list[Any]) -> list[Any]:
        data = {'query': query, 'bindings': bindings}
        d = json.dumps(data).encode('utf-8')
        self.socket.send(d)
        while True:
            sockets = dict(self.poller.poll(1000))
            if self.socket in sockets:
                if sockets[self.socket] == zmq.POLLIN:
                    msg = self.socket.recv()
                    return json.loads(msg)

    # def run(self):
    #     while True:
    #         for i in range(5):
    #             sockets = dict(await poller.poll(1000))
    #             if socket in sockets:
    #                 if sockets[socket] == zmq.POLLIN:
    #                     msg = await socket.recv()
    #                     print('%s: %s\n' % (identity, msg))
    #                     del msg
    #         reqs = reqs + 1
    #         print('Req #%d sent..' % (reqs))
    #         socket.send(b'request #%d' % (reqs))

    #     socket.close()
    #     context.term()
                

if __name__ == '__main__':
    db = MountainsDB()
    output = db.execute('SELECT identifier FROM assets WHERE type=? LIMIT 10', ['C'])
    print(output)

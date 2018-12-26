import sys
import logging
import random

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.queues
import tornado.gen

log_format = '%(levelname) -5s %(asctime)s %(name) -30s %(funcName) -35s %(lineno) -5d: %(message)s'
logging.basicConfig(stream=sys.stdout,
                    format=log_format,
                    level=logging.INFO)
logger = logging.getLogger()


class MessageConsumer(object):
    def __init__(self, queue, callback=None):
        self._queue = queue
        self._callback = callback

    async def start(self):
        async for message in self._queue:
            try:
                if self._callback:
                    self._callback(message)
            finally:
                self._queue.task_done()


class MessageProducer(object):
    def __init__(self, queue):
        self._queue = queue

    async def start(self):
        while True:
            message = 'A produced message!'
            await self._queue.put(message)
            await tornado.gen.sleep(random.uniform(1, 5))


class WebSocketManager(object):
    def __init__(self):
        self._listeners = set()

    def add_websocket(self, websocket):
        self._listeners.add(websocket)

    def remove_websocket(self, websocket):
        self._listeners.discard(websocket)

    def notify_websockets(self, message):
        for listener in self._listeners:
            listener.notify(message)


class MainHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        self.render('templates/index.html')


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        self.application.ws_manager.add_websocket(self)

    def on_close(self):
        self.application.ws_manager.remove_websocket(self)

    def notify(self, message):
        self.write_message(message)


if __name__ == "__main__":
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/ws", WebSocketHandler),
    ])
    application.ws_manager = WebSocketManager()
    application.listen(8888)

    queue = tornado.queues.Queue()

    consumer = MessageConsumer(queue=queue, callback=application.ws_manager.notify_websockets)
    tornado.ioloop.IOLoop.current().spawn_callback(callback=consumer.start)

    producer = MessageProducer(queue=queue)
    tornado.ioloop.IOLoop.current().spawn_callback(callback=producer.start)

    tornado.ioloop.IOLoop.current().start()

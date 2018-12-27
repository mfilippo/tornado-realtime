#!/usr/bin/env python3

"""
This is an example of a Tornado web application featuring real time notifications.

Executing the file with:
    
    $ python3 webserver.py

will start the I/O loop running the Tornado web server, a producer generating some messages and a consumer
that will read these messages. The producer and the consumer share an asynchronous queue, which they use
to exchange the messages. This mechanism allow for more than one consumer/producer.

The consumer action is defined by the function passed as the "callback" argument in the consumer __init__
method. In this case, the only action executed is sending the message to all connected and registered
WebSocket clients.

The WebSocket clients (connections) are handled by the WebSocketManager object, which implements the
Observable behaviour of the Observer Design Pattern. The WebSocketHandler
"""

import sys
import logging
import random

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.queues
import tornado.gen

log_format = '%(levelname) -5s %(asctime)s %(name) -30s %(funcName) -35s %(lineno) -5d: %(message)s'
logging.basicConfig(stream=sys.stdout, format=log_format, level=logging.INFO)
logger = logging.getLogger()


class MessageConsumer(object):
    """
    Basic class implementing the consumer behaviour.
    """

    def __init__(self, queue, callback=None):
        """
        Initialize the consumer instance.

        The function passed as callback must accept one positional argument,
        which will be used to pass the received message.

        :param queue: the queue containing the messages to consume
        :param callback: invoked when a new message is received
        """
        self._queue = queue
        self._callback = callback

    async def start(self):
        """
        Start the consumer.

        :return: None
        """
        async for message in self._queue:
            logger.info('Consuming message: {}'.format(message))
            try:
                if self._callback:
                    self._callback(message)
            finally:
                self._queue.task_done()


class MessageProducer(object):
    """
    Basic class implementing the producer behaviour.
    """

    def __init__(self, queue):
        """
        Initialize the producer instance.

        :param queue: the queue where to put the produced messages
        """
        self._queue = queue

    async def start(self):
        """
        Start the producer.

        :return: None
        """
        i = 1
        while True:
            message = 'Message {}'.format(i)
            logger.info('Produced new message: {}'.format(message))
            await self._queue.put(message)
            await tornado.gen.sleep(random.uniform(1, 5))
            i = i + 1


class WebSocketManager(object):
    """
    The goal of this class is to manage the WebSocket handlers and notify them.
    It is an implementation of the Observer pattern where this class represents the Observable
    and the handlers represent the Observers.
    """

    def __init__(self):
        """
        Initialize the manager.
        """
        self._observers = set()

    def register_websocket(self, websocket):
        """
        Register a new WebSocket handler, usually called by the handler himself. It will be notified
        about new messages.

        :param websocket: a WebSocket handler. It must implement the notify() method
        :return: None
        """
        logger.info('Registering WS handler: {}'.format(websocket))
        self._observers.add(websocket)

    def remove_websocket(self, websocket):
        """
        Remove the WebSocket handler. It will be no longer notified about new messages.

        :param websocket: the WebSocket handler to remove.
        :return: None
        """
        logger.info('Removing WS handler: {}'.format(websocket))
        self._observers.discard(websocket)

    def notify_websockets(self, message):
        """
        Notify all the registered WebSocket handlers about the new received message.

        :param message: the message that will be sent to all registered handlers
        :return: None
        """
        logger.info('Notifying {} websockets'.format(len(self._observers)))
        for observer in self._observers:
            observer.notify(message)


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    """
    Handle WebSocket connections.
    """

    def open(self):
        """
        Handle a new opened connection. It will be registered as listener to the WebSocket manager.

        :return: None
        """
        logger.info('A WS connection is open')
        self.application.ws_manager.register_websocket(self)

    def on_close(self):
        """
        Handle a closed connection, removing it from the WebSocket manager.

        :return: None
        """
        logger.info('A WS connection is closed')
        self.application.ws_manager.remove_websocket(self)

    def notify(self, message):
        """
        Method implementing the Observer behaviour, called by the Observable.

        :param message: the message received by the Observable.
        :return: None
        """
        logger.info('Notified with message: {}'.format(message))
        self.write_message(message)


class MainHandler(tornado.web.RequestHandler):
    """
    Handle the main page.
    """

    @tornado.gen.coroutine
    def get(self):
        """
        Return the main page.

        :return: the HTML page representing the main application.
        """
        logger.info('Main page requested')
        self.render('templates/index.html')


if __name__ == "__main__":
    logger.info('Starting the application')

    # Define the Tornado application
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/ws", WebSocketHandler),
    ])

    # We attach the WS manager as a property of the Tornado application.
    # This way the manager is accessible from inside the WebSocketHandler class.
    application.ws_manager = WebSocketManager()
    application.listen(8888)

    # Define the asynchronous queue shared between consumers and producers
    queue = tornado.queues.Queue()

    # Create and start a consumer
    consumer = MessageConsumer(queue=queue, callback=application.ws_manager.notify_websockets)
    tornado.ioloop.IOLoop.current().spawn_callback(callback=consumer.start)

    # Create and start a producer
    producer = MessageProducer(queue=queue)
    tornado.ioloop.IOLoop.current().spawn_callback(callback=producer.start)

    # Start the I/O loop
    tornado.ioloop.IOLoop.current().start()

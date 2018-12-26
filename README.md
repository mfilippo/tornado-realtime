tornado-realtime
================

A simple Tornado-based server handling real-time notifications by using WebSockets.

Once requested by the client, the (Javascript) application will initiate the WebSocket connection. Each connection will be registered server side and it will be used to push messages to connected clients.

In this example there is a `MessageProducer` instance that generates some messages and puts them inside a queue. In parallel, a `MessageConsumer` instance will read the messages from the queue and perform some actions. In this case the action simply consists of sending the message to all registered WebSocket connections.

### Run

The application can be installed with

```bash
pip3 install -r requirements.txt
```

and can be run with

```bash
python3 webserver.py
```

Assuming the application is running on `localhost:8888` (default port), logs will show the produced messages and all clients connected to `http://localhost:8888` will receive the messaged via WebSocket in real time. The received messages can be seen by inspecting the browser console.
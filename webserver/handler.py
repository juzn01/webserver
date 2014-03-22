class ConnectionHandler(object):
    """Base class for connection-oriented (e.g. TCP) request handler"""
    def __init__(self, request, client_address):
        self.connection = request
        self.client_address = client_address

        # File object to read data from the socket's fd after dup()
        self.received = self.connection.makefile('rb')  # Buffered (default)
        # File object to write data to the socket's fd after dup()
        self.sent = self.connection.makefile('wb', 0)  # Unbuffered

        try:
            self.handle()
        finally:
            self.received.close()
            self.sent.close()

    def handle(self):
        pass


class HTTPRequestHandler(ConnectionHandler):

    def handle(self):
        r = self.received.readline()
        print r
        status_line = 'HTTP/1.1 200 OK\r\n'
        self.sent.write(status_line)
        data = '<html>OK</html>'
        self.sent.write(data)
        self.sent.flush()

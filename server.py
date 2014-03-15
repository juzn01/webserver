import errno
import os
import select
import socket
import sys
import threading


def _eintr_retry(func, *args):
    """Restart a system call interrupted by EINTR"""
    while True:
        try:
            return func(*args)
        except (OSError, select.error) as e:
            if e.args[0] != errno.EINTR:
                raise


class ThreadingTCPServer(object):
    """A multi-threaded TCP server"""

    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    backlog = 5

    def __init__(self, server_address, RequestHandler):
        """
        :param server_address: a pair (host, port)
        :param RequestHandler: request handler class
        """
        self.server_address = server_address
        self.RequestHandler = RequestHandler
        self.socket = socket.socket(self.address_family,
                                    self.socket_type)
        self.socket.bind(self.server_address)
        self.socket.listen(self.backlog)

    def start(self, poll_interval=0.5):
        """
        Start the server

        Use `select` system call (with `poll_interval` argument) to get ready
        sockets without blocking
        """

        while True:
            r, w, e = _eintr_retry(select.select, [self.socket.fileno()],
                                   [], [], poll_interval)
            if self in r:
                self.handle_request()

    def handle_request(self):
        try:
            request, client_address = self.get_request()
        except socket.error:
            return
        try:
            self.process_request(request, client_address)
        except:
            self.handle_error(client_address)
            request.close()

    def handle_error(self, client_address):
        msg = 'Error processing request from %s, %d' % client_address
        sys.stderr.write(msg)

    def process_request(self, request, client_address):
        """Process requests in threads"""
        t = threading.Thread(target=self._thread_process_request,
                             args=(request, client_address),
                             daemon=False)
        t.start()

    def _thread_process_request(self, request, client_address):
        """Worker thread"""
        self.RequestHandlerClass(request, client_address)
        request.close()

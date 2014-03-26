#!/usr/bin/env python
import errno
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

        # Set SO_REUSEADDR
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.socket.listen(self.backlog)

        # Meta information
        self._addr = self.server_address[0].strip() or '0.0.0.0'
        self._port = self.server_address[1]

    def start(self, timeout=0.5):
        """
        Start the server

        Use `select` system call (with `poll_interval` argument) to get ready
        sockets without blocking
        """
        msg = 'Starting sever bound to %s:%d\n' % (self._addr, self._port)
        sys.stderr.write(msg)
        while True:
            # import pdb
            # pdb.set_trace()
            # print count
            r, w, e = _eintr_retry(select.select, [self.socket.fileno()],
                                   [], [], timeout)
            if self.socket.fileno() in r:
                self.handle_request()

    def handle_request(self):
        # import pdb
        # pdb.set_trace()
        try:
            request, client_address = self.socket.accept()
        except socket.error:
            return
        try:
            # Dispatch the request to a thread
            self.process_request(request, client_address)
        except Exception, e:
            # raise e
            self.handle_error(client_address)
            request.close()

    def handle_error(self, client_address):
        msg = 'Error processing request from %s:%d\n' % client_address
        sys.stderr.write(msg)

    def process_request(self, request, client_address):
        """Process requests in threads"""
        t = threading.Thread(target=self._thread_process_request,
                             args=(request, client_address))
        t.daemon = False
        t.start()

    def _thread_process_request(self, request, client_address):
        """Worker thread"""
        try:
            self.RequestHandler(request, client_address)
        except Exception, e:
            # raise e
            self.handle_error(client_address)
        request.close()

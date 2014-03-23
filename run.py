#!/usr/bin/env python

import signal
import sys
import os
from webserver.server import ThreadingTCPServer
from webserver.handler import HTTPRequestHandler


def sigint_handler(signum, frame):
    sys.stderr.write('\n')
    os._exit(1)

signal.signal(signal.SIGINT, sigint_handler)


def run_server(port):
    server_address = ('', port)
    server = ThreadingTCPServer(server_address, HTTPRequestHandler)
    server.start()

if __name__ == '__main__':
    usage = './run.py [port]\n'
    port = 8080
    if len(sys.argv) == 2:
        if not sys.argv[1].isdigit():
            msg = 'Invalid port number\n'
            sys.stderr.write(msg)
            sys.exit(1)
        port = int(sys.argv[1])
    elif len(sys.argv) > 2:
        sys.stderr.write(usage)
        sys.exit(1)
    run_server(port)

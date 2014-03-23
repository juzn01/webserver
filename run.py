import signal
import sys
import os
from webserver.server import ThreadingTCPServer
from webserver.handler import HTTPRequestHandler


def sigint_handler(signum, frame):
    sys.stderr.write('\n')
    os._exit(1)

signal.signal(signal.SIGINT, sigint_handler)


def run_server():
    server_address = ('', 8080)
    server = ThreadingTCPServer(server_address, HTTPRequestHandler)
    server.start()


if __name__ == '__main__':
    run_server()

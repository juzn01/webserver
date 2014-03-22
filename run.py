from webserver.server import ThreadingTCPServer
from webserver.handler import HTTPRequestHandler


def run_server():
    server_address = ('', 8000)
    server = ThreadingTCPServer(server_address, HTTPRequestHandler)
    server.start()


if __name__ == '__main__':
    run_server()

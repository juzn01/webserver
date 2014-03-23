import cgi
import mimetools
import os
import shutil
import socket
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import urllib
from webserver import __version__


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
            self.sent.close()
            self.received.close()

    def handle(self):
        pass


class HTTPRequestHandler(ConnectionHandler):
    """Minimum HTTP request handler"""

    http_version = 'HTTP/1.1'  # Default supported HTTP version
    server_version = 'Webserver/' + __version__
    supported_http_versions = ('HTTP/1.0', 'HTTP/1.1')
    index_files = ('index.html', 'index.htm')
    default_content_type = 'text/html'

    def do_GET(self):
        f = self.send_head()
        if f:
            try:
                shutil.copyfileobj(f, self.sent)
            finally:
                f.close()

    def do_HEAD(self):
        f = self.send_head()
        if f:
            f.close()

    def send_head(self):
        """Send response status line and headers, and return a file object"""
        absolute_path = self.get_path()
        if os.path.isdir(absolute_path):
            if not self.path.endswith('/'):
                # Redirect the browser appending an ending slash
                self.send_response(301)
                self.send_header('Location', self.path + '/')
                self.end_headers()
                return
            for index_file in self.index_files:
                index = os.path.join(absolute_path, index_file)
                if os.path.exists(index):
                    absolute_path = index
                    break
            else:
                return self.list_directory()
        try:
            f = open(absolute_path, 'rb')
        except IOError:
            self.send_error(404)
            return
        try:
            self.send_header("Content-type", self.default_content_type)
            fs = os.fstat(f.fileno())
            self.send_header("Content-Length", str(fs[6]))
            self.end_headers()
            return f
        except:
            raise
            f.close()

    def list_directory(self, path):
        try:
            file_list = os.listdir(path)
        except os.error:
            self.send_error(404)
            return
        file_list.sort(key=lambda a: a.lower())
        f = StringIO()
        dpath = cgi.escape(urllib.unquote(self.path))
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<title>Directory listing for %s</title>\n" % dpath)
        f.write("<body>\n<h2>Directory listing for %s</h2>\n" % dpath)
        f.write("<hr>\n<ul>\n")
        for name in file_list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write('<li><a href="%s">%s</a>\n'
                    % (urllib.quote(linkname), cgi.escape(displayname)))
        f.write("</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", self.default_content_type)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def get_path(self):
        """
        Get the absolute path of the requested resource (file or directory)
        """
        relative_path = self.path.lstrip('/')
        absolute_path = os.path.join(os.getcwd(), relative_path)
        return absolute_path

    def handle_request(self):
        """Handle a specific request and log error if any"""
        try:
            request_line = self.received.readline().rstrip('\r\n')

            # Request line is empty
            if not request_line:
                self.log_error('Empty request line')
                self.close_connection = True
                return

            self.request_line = request_line
            if not self.parse_request():
                return

            method_func = 'do_' + self.method
            if not hasattr(self, method_func):
                # Unsupported HTTP method
                self.send_error(501)
                return
            method = getattr(self, method_func)
            # Call this method function
            method()

        except socket.timeout:
            self.log_error('Request timeout')
            self.close_connection = True

    def parse_request(self):
        """
        Parse a specific request and send error if any
        Return False if error occurs; True if success
        """
        try:
            method, path, request_version = self.request_line.split()
        except:
            # Bad request syntax
            self.send_error(400)
            return False
        if request_version not in self.supported_http_versions:
            self.send_error(505)
            return False

        self.method = method
        self.path = path
        self.request_version = request_version

        # Get optional headers
        self.headers = mimetools.Message(self.received, 0)
        connection_type = self.headers('Connection', '')
        if connection_type.lower() == 'close':
            self.close_connection = True
        elif (connection_type.lower() == 'keep-alive' and
              self.request_version == 'HTTP/1.1'):
            self.close_connection = False
        return True

    def handle(self):
        """Handle the request one at a time or keep-alive (loop)"""
        self.close_connection = True
        self.handle_request()
        while not self.close_connection:
            self.handle_request()

    def send_response(self, code):
        self.log_request(code)
        status_line = '%s %d %s\r\n' % (self.http_version, code,
                                        self.status_codes[code][0])
        self.sent.write(status_line)

    def send_header(self, name, value):
        """Send a single header"""
        header = '%s: %s\r\n' % (name, value)
        self.sent.write(header)

        # Close or keep connection depending on header
        if name.lower() == 'connection':
            if value.lower() == 'close':
                self.close_connection = True
            elif value.lower() == 'keep-alive':
                self.close_connection = False

    def end_headers(self):
        self.sent.write('\r\n')

    def send_error(self, code):
        """Send respons with error code and close connection"""
        self.send_response(code)
        self.send_header('Connection', 'close')
        self.end_headers()

    def log_request(self, code):
        """
        Log every request upon sending response in the following format:

            `client_address`, `code`, `message`

        """
        msg = '%s %d %s\n' % (self.client_address[0], code,
                              self.status_codes[code][0])
        sys.stderr.write(msg)

    def log_error(self, message):
        """
        Log error without sending response
        """
        msg = '%s %s\n' % (self.client_address[0], message)
        sys.stderr.write(msg)

    # RFC 2616
    status_codes = {
        100: ('Continue', 'Request received, please continue'),
        101: ('Switching Protocols',
              'Switching to new protocol; obey Upgrade header'),

        200: ('OK', 'Request fulfilled, document follows'),
        201: ('Created', 'Document created, URL follows'),
        202: ('Accepted',
              'Request accepted, processing continues off-line'),
        203: ('Non-Authoritative Information', 'Request fulfilled from cache'),
        204: ('No Content', 'Request fulfilled, nothing follows'),
        205: ('Reset Content', 'Clear input form for further input.'),
        206: ('Partial Content', 'Partial content follows.'),

        300: ('Multiple Choices',
              'Object has several resources -- see URI list'),
        301: ('Moved Permanently', 'Object moved permanently -- see URI list'),
        302: ('Found', 'Object moved temporarily -- see URI list'),
        303: ('See Other', 'Object moved -- see Method and URL list'),
        304: ('Not Modified',
              'Document has not changed since given time'),
        305: ('Use Proxy',
              'You must use proxy specified in Location to access this '
              'resource.'),
        307: ('Temporary Redirect',
              'Object moved temporarily -- see URI list'),

        400: ('Bad Request',
              'Bad request syntax or unsupported method'),
        401: ('Unauthorized',
              'No permission -- see authorization schemes'),
        402: ('Payment Required',
              'No payment -- see charging schemes'),
        403: ('Forbidden',
              'Request forbidden -- authorization will not help'),
        404: ('Not Found', 'Nothing matches the given URI'),
        405: ('Method Not Allowed',
              'Specified method is invalid for this resource.'),
        406: ('Not Acceptable', 'URI not available in preferred format.'),
        407: ('Proxy Authentication Required', 'You must authenticate with '
              'this proxy before proceeding.'),
        408: ('Request Timeout', 'Request timed out; try again later.'),
        409: ('Conflict', 'Request conflict.'),
        410: ('Gone',
              'URI no longer exists and has been permanently removed.'),
        411: ('Length Required', 'Client must specify Content-Length.'),
        412: ('Precondition Failed', 'Precondition in headers is false.'),
        413: ('Request Entity Too Large', 'Entity is too large.'),
        414: ('Request-URI Too Long', 'URI is too long.'),
        415: ('Unsupported Media Type', 'Entity body in unsupported format.'),
        416: ('Requested Range Not Satisfiable',
              'Cannot satisfy request range.'),
        417: ('Expectation Failed',
              'Expect condition could not be satisfied.'),

        500: ('Internal Server Error', 'Server got itself in trouble'),
        501: ('Not Implemented',
              'Server does not support this operation'),
        502: ('Bad Gateway', 'Invalid responses from another server/proxy.'),
        503: ('Service Unavailable',
              'The server cannot process the request due to a high load'),
        504: ('Gateway Timeout',
              'The gateway server did not receive a timely response'),
        505: ('HTTP Version Not Supported', 'Cannot fulfill request.'),
    }

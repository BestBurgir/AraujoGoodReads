from functools import cached_property
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse
import redis
import re
# Código basado en:
# https://realpython.com/python-http-server/
# https://docs.python.org/3/library/http.server.html
# https://docs.python.org/3/library/http.cookies.html


mappings = [
    (r"^/books/(?P<book_id>\d+)$", "get_book"),

]

r = redis.StrictRedis(host="localhost", port=6379, db=0)

class WebRequestHandler(BaseHTTPRequestHandler):

    

    @cached_property
    def url(self):
        return urlparse(self.path)

    @cached_property
    def query_data(self):
        return dict(parse_qsl(self.url.query))

    @cached_property
    def post_data(self):
        content_length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(content_length)

    @cached_property
    def form_data(self):
        return dict(parse_qsl(self.post_data.decode("utf-8")))

    @cached_property
    def cookies(self):
        return SimpleCookie(self.headers.get("Cookie"))

    def get_params(self, pattern, path):
        m = re.match(pattern, path)
        if m:
            return m.groupdict()

    def get_book(self, book_id):
        # self.send_response(200)
        # self.send_header("Content-Type", "text/html")
        # self.end_headers()
        #book_info = f"<h1>El libro solicitado es: {book_id}</h1>".encode("utf-8")
        book_info = r.get(f"book:{book_id}") or "No existe el libro".encode("utf-8")
        self.wfile.write(book_info)

    def do_GET(self):
        pattern = r"/books/(?P<book_id>\d+)"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        match = self.get_params(pattern, self.path)
        if match:
            self.get_book(match["book_id"])
        else:
            self.wfile.write(f"<h1>El path {self.path} es incorrecto</h1>".decode("utf-8"))

    # def get_response(self):
    #     return f"""
    #     <h1> Hola Web </h1>
    #     <p>  {self.path}         </p>
    #     <p>  {self.headers}      </p>
    #     <p>  {self.cookies}      </p>
    #     <p>  {self.query_data}   </p>
    # """


if __name__ == "__main__":
    print("Server starting...")
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
    server.serve_forever()

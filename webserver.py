from functools import cached_property
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse
import redis
import re
import uuid
# Código basado en:
# https://realpython.com/python-http-server/
# https://docs.python.org/3/library/http.server.html
# https://docs.python.org/3/library/http.cookies.html


mappings = [
    (r"^/books/(?P<book_id>\d+)$", "get_book"),
    (r"^/search", "search"),
    (r"^/$", "index"),
]

r = redis.StrictRedis(host="localhost", port=6379, db=0)

class WebRequestHandler(BaseHTTPRequestHandler):

    @property
    def url(self):
        return urlparse(self.path)

    @property
    def query_data(self):
        return dict(parse_qsl(self.url.query))

    def search(self):
        self.send_response(200)
        self.send_header("content-type", "text/html")
        self.end_headers()
        index_page = f"<h1>{self.path}</h1>".encode("utf-8")
        self.wfile.write(index_page)

    def cookies(self):
        return SimpleCookie(self.headers.get("Cookie"))
    
    def get_session(self):
        cookies = self.cookies()
        if not cookies or "session_id" not in cookies:
            session_id = uuid.uuid4()
        else:
            session_id = cookies["session_id"].value
        return session_id
    
    def write_session_cookie(self, session_id):
        cookies = SimpleCookie()
        cookies["session_id"] = session_id
        cookies["session_id"]["max-age"] = 1000
        self.send_header("Set-Cookie", cookies.output(header=""))

    def do_GET(self):
        self.url_mapping_response()

    def url_mapping_response(self):
        for pattern, method in mappings:
            match = self.get_params(pattern, self.path)
            print(match)  # {'book_id': '1'}
            if match is not None:
                md = getattr(self, method)
                md(**match)
                return
            
        self.send_response(404)
        self.end_headers()
        self.wfile.write("Not Found".encode("utf-8"))

    def get_params(self, pattern, path):
        match = re.match(pattern, path)
        if match:
            return match.groupdict()

    def index(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        index_page = """
        <h1>Bienvenidos a los Libros </h1>
        <form action="/search" method="get">
            <input type="text" name="q" />
            <input type="submit" value="Buscar Libro" />
        </form>
        """.encode("utf-8")
        self.wfile.write(index_page)

    def get_book(self, book_id):
        session_id = self.get_session()
        r.lpush(f"session:{session_id}", f"book:{book_id}")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.write_session_cookie(session_id)
        self.end_headers()
        #book_info = f"<h1> Info de Libro {book_id} es correcto </h1>".encode("utf-8")
        book_info = r.get(f"book_id:{book_id}") or "No existe el libro".encode("utf-8")
        self.wfile.write(str(book_info).encode("utf-8"))
        self.wfile.write(f"session:{session_id}".encode()("utf-8"))
        book_list = r.lrange(f"session:{session_id}", 0, -1)
        for book in book_list:
            self.wfile.write(f"book:{book}".encode("utf-8"))


    # def get_response(self):
    #     return f"""
    #     <h1> Hola Web </h1>
    #     <p>  {self.path}         </p>
    #     <p>  {self.headers}      </p>
    #     <p>  {self.cookies}      </p>
    #     <p>  {self.query_data}   </p>
    # """


print("Server starting.")
server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
server.serve_forever()

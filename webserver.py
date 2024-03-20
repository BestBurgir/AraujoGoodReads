from functools import cached_property
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
import mimetypes
from urllib.parse import parse_qsl, urlparse
import redis
import re
import uuid
import json
import os
from http import HTTPStatus
# Código basado en:
# https://realpython.com/python-http-server/
# https://docs.python.org/3/library/http.server.html
# https://docs.python.org/3/library/http.cookies.html

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Configuración de Jinja2
env = Environment(
    loader=FileSystemLoader('html'),
    autoescape=select_autoescape(['html', 'xml'])
)

mappings = [
    (r"^/books/(?P<book_id>\d+)$", "get_book"),
    (r"^/search", "get_by_search"),
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
        self.send_header("content-type","text/html")
        self.end_headers()
        index_page = f"<h1>{self.query_data['q'].split()}</h1>".encode("utf-8")
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
        if self.path.startswith('/public/'):
            # Intenta servir archivos estáticos.
            self.serve_static_file()
        else:
            self.url_mapping_response()

    def serve_static_file(self):
        # Construye la ruta al archivo estático, asumiendo que `public` está en la misma carpeta que tu script
        root = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(root, self.path[1:])  # [1:] elimina la primera barra para evitar rutas absolutas

        # Verifica si el archivo existe y es un archivo (no un directorio)
        if os.path.exists(path) and os.path.isfile(path):
            # Determina el tipo MIME para el encabezado Content-Type
            mime_type, _ = mimetypes.guess_type(path)
            mime_type = mime_type or 'application/octet-stream'

            # Lee el archivo y lo envía
            with open(path, 'rb') as file:
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', mime_type)  # Usa el tipo MIME correcto
                self.end_headers()
                self.wfile.write(file.read())
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def url_mapping_response(self):
        for pattern, method in mappings:
            match = self.get_params(pattern, self.path)
            # print(match)  # {'book_id': '1'}
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
        
        # Cargar la plantilla con Jinja2
        template = env.get_template('index.html')

        # Renderizar la plantilla con cualquier dato que quieras pasar
        response = template.render(titulo='Página de Inicio')
        self.wfile.write(response.encode("utf-8"))

        # with open('html/index.html') as f:
        #     response = f.read()
        # self.wfile.write(response.encode("utf-8"))   
        # index_page = """
        # <h1>Bienvenidos a los Libros </h1>
        # <form action="/search" method="get">
        #     <input type="text" name="q" />
        #     <input type="submit" value="Buscar Libro" />
        # </form>
        # """.encode("utf-8")
        # self.wfile.write(index_page)

    def load_books_from_json(self,json_path='data_books.json'):
        with open(json_path, 'r', encoding='utf-8') as file:
            books = json.load(file)
        return books

    def get_by_search(self):
        if self.query_data and 'q' in self.query_data:
            booksInter = r.sinter(self.query_data['q'].split(' '))
            books_info = []
            all_books = self.load_books_from_json()  # Carga todos los libros del JSON
            # print(booksInter)
            # Decodificar los resultados y agregarlos a la lista
            for b in booksInter:
                book_id = b.decode('utf-8')  # Decodifica el ID del libro
                # Busca en el JSON la información del libro por su ID
                book_data = next((book for book in all_books if book['id'] == book_id), None)
                if book_data:
                    books_info.append(book_data)

            # Si no se encontraron libros, redirigir a get_index
            if not books_info:
                self.index()
            else:
                self.render_search_page(books_info)
                    
        
    def render_search_page(self, books_info):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        # Asume que tienes un template 'search.html' listo para ser renderizado
        template = env.get_template('search.html')
        response = template.render(books=books_info)
        self.wfile.write(response.encode("utf-8"))


    def get_recomendation(self,session_id, book_id):
        books=r.lrange(f"session:{session_id}",0,-1)
        # print(session_id, books)

        books_read = {book.decode('utf-8').split(':')[1] for book in books}

        all_books = {'1','2','3','4','5','6','7'}

        books_to_recommend = all_books-books_read
        if len(books_read)>=3:
            if books_to_recommend:
                return f"Te recomendamos leer el libro : {books_to_recommend.pop()}"
            else: 
                return "Ya has leido todos los libros"
        else:
            return "Lee el menos tres libros para obtener recomendaciones"

    def get_book(self, book_id):
        session_id = self.get_session()
        r.lpush(f"session:{session_id}", f"book:{book_id}")
        book_recomendation = self.get_recomendation(session_id, book_id)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.write_session_cookie(session_id)
        self.end_headers()

        #book_info = f"<h1> Info de Libro {book_id} es correcto </h1>".encode("utf-8")
        book_info = r.get(f"book:{book_id}")

        if book_info is not None:
            book_info=book_info.decode('utf-8')
        else:
            book_info = "<h1>No existe el libro</h1>"    

        #book_info=book_info + f"session id:{session_id}".encode("utf-8")
        self.wfile.write(str(book_info).encode("utf-8"))
        
        self.wfile.write(f"session:{session_id}\n".encode("utf-8"))
        
        book_list=r.lrange(f"session:{session_id}",0,-1)
        for book in book_list:
            book_id = book.decode('utf-8')
            self.wfile.write(book_id.encode('utf-8'))

        if book_recomendation:
           self.wfile.write(f"<p>Recomendacion:{book_recomendation}</p>\n".encode('utf-8'))


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

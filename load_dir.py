import json
import re 
import redis
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

r = redis.StrictRedis(host='localhost', port=6379, db=0)
env = Environment(loader=FileSystemLoader('html'), autoescape=True)

def create_index(book_id, html):
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text().split()
    for word in text:
        r.sadd(word, book_id)

def load_books_from_json(json_path):
    with open(json_path, 'r') as file:
        books = json.load(file)
    
    for book in books:
        template = env.get_template('/books/book.html')
        html = template.render(book=book)
        
        # Guarda el HTML generado en Redis
        r.set(f"book:{book['id']}", html)
        
        # Crea un índice para el libro
        create_index(book['id'], html)
        print(f"Book {book['title']} loaded into Redis")

# Llamada a la función
load_books_from_json('data_books.json')
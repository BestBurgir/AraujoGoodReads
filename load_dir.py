import os
import re 
import redis

r = redis.StrictRedis(host='localhost', port=6379, db=0)

def load_dir(path):
    files = os.listdir(path)

    # files = [f for f in files if re.search(r"")]
    for f in files:
        match = re.match(r'^book(\d+).html$', f)
        if match:
            with open(path + f, 'r') as file:
                html = file.read()
                book_id = match.group(1)
                r.set(f"book:{book_id}", html)
        else:
            print(f"El archivo {f} no es un libro")

load_dir('./html/books/')
import sys
import time
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from models.models import get_db_connection

def update_images():
    print("Conectando a la base de datos...")
    
    # Diccionario de URLs locales (imágenes generadas)
    urls = {
        'guitar': '/static/imagenes productos/premium_guitar.jpg',
        'bass': '/static/imagenes productos/premium_bass.jpg',
        'violin': '/static/imagenes productos/premium_violin.jpg',
        'piano': '/static/imagenes productos/premium_piano.jpg',
        'drums': '/static/imagenes productos/premium_drums.jpg',
        'woodwind': '/static/imagenes productos/premium_woodwind.jpg',
        'brass': '/static/imagenes productos/premium_brass.jpg',
        'ukulele': '/static/imagenes productos/premium_ukulele.jpg',
        'percussion': '/static/imagenes productos/premium_percussion.jpg',
        'default': '/static/imagenes productos/premium_instrument.jpg'
    }

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, nombre FROM productos")
            productos = cursor.fetchall()
            print(f"Se encontraron {len(productos)} productos.")
            
            for p in productos:
                nombre = p['nombre'].lower()
                
                keyword = 'default'
                if 'guitarra' in nombre: keyword = 'guitar'
                elif 'bajo' in nombre: keyword = 'bass'
                elif 'bater' in nombre or 'bombo' in nombre or 'caja' in nombre: keyword = 'drums'
                elif 'piano' in nombre or 'teclado' in nombre or 'sintetizador' in nombre: keyword = 'piano'
                elif 'viol' in nombre: keyword = 'violin'
                elif 'flauta' in nombre or 'clarinete' in nombre or 'saxo' in nombre: keyword = 'woodwind'
                elif 'tromp' in nombre or 'tuba' in nombre or 'corno' in nombre or 'eufonio' in nombre: keyword = 'brass'
                elif 'ukulele' in nombre or 'cuatro' in nombre or 'tiple' in nombre or 'charango' in nombre or 'arpa' in nombre: keyword = 'ukulele'
                elif 'percusi' in nombre or 'conga' in nombre or 'bongo' in nombre or 'timbal' in nombre or 'maraca' in nombre: keyword = 'percussion'
                
                url = urls.get(keyword, urls['default'])
                
                cursor.execute("UPDATE productos SET imagen_url = %s WHERE id = %s", (url, p['id']))
            conn.commit()
            print("Todas las imagenes han sido actualizadas con exito a locales!")

if __name__ == '__main__':
    update_images()

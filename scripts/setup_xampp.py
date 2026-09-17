"""
============================================================================
SCRIPT AUTOMATIZADO DE CONFIGURACION PARA XAMPP - ROCK CORPORATION
============================================================================
Este script verifica que MySQL de XAMPP esté en ejecución (puerto 3306),
crea automáticamente la base de datos 'rock corporation' y carga las tablas,
el usuario administrador inicial y los 10 productos en pesos colombianos (COP).
============================================================================
"""

import sys
import os
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Configurar salida UTF-8 para consola Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import pymysql
except ImportError:
    print("[X] Falta la libreria PyMySQL. Instalala ejecutando: pip install pymysql")
    sys.exit(1)

from models.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT
from models.models import init_db, obtener_productos, get_db_connection

def verificar_y_configurar_xampp():
    print("[*] Conectando con el servidor MySQL de XAMPP (127.0.0.1:3306)...")
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            charset="utf8mb4",
            autocommit=True
        )
        print("[OK] Conexion exitosa con el servidor MySQL de XAMPP.")
    except Exception as e:
        print(f"[X] Error al conectar con XAMPP MySQL: {e}")
        print("[!] Asegurate de abrir XAMPP Control Panel e Iniciar el servicio 'MySQL'.")
        return False

    try:
        print("[*] Inicializando base de datos 'rock corporation' y migrando esquemas...")
        init_db()
        print("[OK] Base de datos 'rock corporation' configurada correctamente en XAMPP.")

        productos = obtener_productos()
        print(f"[+] Total de productos activos en XAMPP MySQL: {len(productos)}")

        with get_db_connection() as conn_db:
            with conn_db.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
                usuarios_count = cursor.fetchone()["total"]
                print(f"[+] Total de usuarios registrados en XAMPP: {usuarios_count}")

        print("\n=======================================================")
        print(" [!] CONFIGURACION DE XAMPP COMPLETADA CON EXITO!")
        print(" [1] Inicia tu servidor web ejecutando: python app.py")
        print(" [2] Accede a phpMyAdmin: http://localhost/phpmyadmin/")
        print("=======================================================")
        return True
    except Exception as e:
        print(f"[X] Error durante la configuracion de las tablas: {e}")
        return False

if __name__ == "__main__":
    verificar_y_configurar_xampp()

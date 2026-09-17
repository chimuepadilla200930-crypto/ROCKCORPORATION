"""
============================================================================
CAPA MODELO - CONEXION Y MIGRACIONES DE BASE DE DATOS - ROCK CORPORATION
============================================================================
"""

import os
from contextlib import contextmanager
from pymysql import connect
from pymysql.cursors import DictCursor
from pymysql.err import OperationalError

from .config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, MYSQL_SSL

@contextmanager
def get_db_connection(database=DB_NAME):
    kwargs = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "cursorclass": DictCursor,
        "autocommit": True,
        "charset": "utf8mb4",
    }
    if database:
        kwargs["database"] = database
    if MYSQL_SSL:
        kwargs["ssl"] = {"ssl_mode": "REQUIRED"}

    conexion = connect(**kwargs)
    try:
        yield conexion
    finally:
        conexion.close()


def init_db():
    try:
        with get_db_connection(database=None) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
    except Exception as error:
        pass

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS productos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(150) NOT NULL UNIQUE,
                    descripcion TEXT NULL,
                    imagen_url VARCHAR(500) NULL,
                    precio DECIMAL(10, 2) NOT NULL,
                    stock INT NOT NULL DEFAULT 0,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre_completo VARCHAR(150) NOT NULL,
                    correo VARCHAR(150) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    rol VARCHAR(50) NOT NULL DEFAULT 'Cliente',
                    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
                    foto_perfil VARCHAR(500) NULL,
                    direccion_casa VARCHAR(255) NULL,
                    ciudad VARCHAR(100) NULL,
                    codigo_postal VARCHAR(50) NULL,
                    tarjeta_enmascarada VARCHAR(100) NULL,
                    metodo_pago_guardado VARCHAR(100) NULL,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pedidos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    usuario_id INT NULL,
                    nombre_cliente VARCHAR(150) NOT NULL,
                    correo_cliente VARCHAR(150) NOT NULL,
                    direccion VARCHAR(255) NOT NULL,
                    ciudad VARCHAR(100) NOT NULL,
                    codigo_postal VARCHAR(50) NOT NULL,
                    total DECIMAL(10, 2) NOT NULL,
                    metodo_pago VARCHAR(100) NOT NULL DEFAULT 'Tarjeta de Crédito',
                    estado_envio VARCHAR(50) NOT NULL DEFAULT 'En preparación',
                    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    fecha_pedido TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS detalle_pedidos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    pedido_id INT NOT NULL,
                    producto_id INT NULL,
                    nombre_producto VARCHAR(150) NOT NULL,
                    precio_unitario DECIMAL(10, 2) NOT NULL,
                    cantidad INT NOT NULL,
                    subtotal DECIMAL(10, 2) NOT NULL,
                    FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
                    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            asegurar_columnas_usuarios(cursor)
            asegurar_columnas_productos(cursor)
            asegurar_columnas_pedidos(cursor)


def asegurar_columnas_usuarios(cursor):
    columnas_necesarias = {
        "foto_perfil": "ALTER TABLE usuarios ADD COLUMN foto_perfil VARCHAR(500) NULL AFTER rol",
        "direccion_casa": "ALTER TABLE usuarios ADD COLUMN direccion_casa VARCHAR(255) NULL AFTER foto_perfil",
        "ciudad": "ALTER TABLE usuarios ADD COLUMN ciudad VARCHAR(100) NULL AFTER direccion_casa",
        "codigo_postal": "ALTER TABLE usuarios ADD COLUMN codigo_postal VARCHAR(50) NULL AFTER ciudad",
        "tarjeta_enmascarada": "ALTER TABLE usuarios ADD COLUMN tarjeta_enmascarada VARCHAR(100) NULL AFTER codigo_postal",
        "metodo_pago_guardado": "ALTER TABLE usuarios ADD COLUMN metodo_pago_guardado VARCHAR(100) NULL AFTER tarjeta_enmascarada",
    }

    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'usuarios'
        """,
        (DB_NAME,),
    )
    columnas_actuales = {fila["COLUMN_NAME"] for fila in cursor.fetchall()}

    for columna, alter_sql in columnas_necesarias.items():
        if columna not in columnas_actuales:
            cursor.execute(alter_sql)


def asegurar_columnas_productos(cursor):
    columnas_necesarias = {
        "descripcion": "ALTER TABLE productos ADD COLUMN descripcion TEXT NULL AFTER nombre",
        "imagen_url": "ALTER TABLE productos ADD COLUMN imagen_url VARCHAR(500) NULL AFTER descripcion",
    }

    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'productos'
        """,
        (DB_NAME,),
    )
    columnas_actuales = {fila["COLUMN_NAME"] for fila in cursor.fetchall()}

    for columna, alter_sql in columnas_necesarias.items():
        if columna not in columnas_actuales:
            cursor.execute(alter_sql)


def asegurar_columnas_pedidos(cursor):
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'pedidos'
        """,
        (DB_NAME,),
    )
    columnas_actuales = {fila["COLUMN_NAME"] for fila in cursor.fetchall()}
    if "fecha_creacion" not in columnas_actuales:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
    if "fecha_pedido" not in columnas_actuales:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN fecha_pedido TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")

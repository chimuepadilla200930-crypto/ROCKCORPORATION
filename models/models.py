import os
import sqlite3
from threading import Lock
from uuid import uuid4

from flask import session
import pymysql
from pymysql.cursors import DictCursor

from .config import *
from .sqlite_adapter import SQLiteConnectionWrapper, init_sqlite_schema
from .postgres_adapter import PgConnectionWrapper, init_postgres_schema

DB_INITIALIZED = False
DB_INIT_LOCK = Lock()
USE_SQLITE = False


# MODELO - CATALOGO BASE
# ============================================================================

def obtener_imagen_instrumento(familia, indice):
    keyword = familia.split(" ")[0].lower()
    urls = {
        'guitarra': '/static/imagenes productos/premium_guitar.jpg',
        'bajo': '/static/imagenes productos/premium_bass.jpg',
        'violin': '/static/imagenes productos/premium_violin.jpg',
        'piano': '/static/imagenes productos/premium_piano.jpg',
        'teclado': '/static/imagenes productos/premium_piano.jpg',
        'bater': '/static/imagenes productos/premium_drums.jpg',
        'flauta': '/static/imagenes productos/premium_woodwind.jpg',
        'tromp': '/static/imagenes productos/premium_brass.jpg',
        'arpa': '/static/imagenes productos/premium_ukulele.jpg',
        'default': '/static/imagenes productos/premium_instrument.jpg'
    }
    
    for key in urls.keys():
        if key in keyword:
            return urls[key]
    return urls['default']

CATALOGO_10_INSTRUMENTOS = [
    (
        "Guitarra ElÃƒÆ’Ã‚Â©ctrica Pro",
        "Guitarra elÃƒÆ’Ã‚Â©ctrica profesional con cuerpo de caoba y pastillas de alta ganancia.",
        "/static/imagenes productos/premium_guitar.jpg",
        5000000.00,
        8,
    ),
    (
        "Guitarra AcÃƒÆ’Ã‚Âºstica Classic",
        "Guitarra acÃƒÆ’Ã‚Âºstica de madera seleccionada con sonido cÃƒÆ’Ã‚Â¡lido y resonancia profunda.",
        "/static/imagenes productos/premium_guitar.jpg",
        1800000.00,
        12,
    ),
    (
        "Bajo ElÃƒÆ’Ã‚Â©ctrico Studio",
        "Bajo elÃƒÆ’Ã‚Â©ctrico de 4 cuerdas ideal para rock, funk y grabaciÃƒÆ’Ã‚Â³n profesional en estudio.",
        "/static/imagenes productos/premium_bass.jpg",
        3560000.00,
        6,
    ),
    (
        "Piano Digital Deluxe",
        "Piano digital de 88 teclas pesadas con respuesta al tacto y mÃƒÆ’Ã‚Âºltiples voces de piano.",
        "/static/imagenes productos/premium_piano.jpg",
        5800000.00,
        5,
    ),
    (
        "BaterÃƒÆ’Ã‚Â­a AcÃƒÆ’Ã‚Âºstica Stage",
        "Set completo de baterÃƒÆ’Ã‚Â­a acÃƒÆ’Ã‚Âºstica con platillos de bronce y herrajes reforzados.",
        "/static/imagenes productos/premium_drums.jpg",
        7400000.00,
        4,
    ),
    (
        "SaxofÃƒÆ’Ã‚Â³n Alto Gold",
        "SaxofÃƒÆ’Ã‚Â³n alto en Mi bemol con acabado dorado y sonido brillante para jazz y bandas.",
        "/static/imagenes productos/premium_woodwind.jpg",
        4400000.00,
        7,
    ),
    (
        "Trompeta de Concierto",
        "Trompeta en Si bemol de latÃƒÆ’Ã‚Â³n dorado con afinaciÃƒÆ’Ã‚Â³n precisa y estuche rÃƒÆ’Ã‚Â­gido.",
        "/static/imagenes productos/premium_brass.jpg",
        2480000.00,
        9,
    ),
    (
        "ViolÃƒÆ’Ã‚Â­n de Concierto",
        "ViolÃƒÆ’Ã‚Â­n 4/4 tallado a mano con arco de madera de brasil y estuche acolchado.",
        "/static/imagenes productos/premium_violin.jpg",
        3120000.00,
        6,
    ),
    (
        "Set de Congas Latinas",
        "Pareja de congas de madera de roble con parches de cuero natural y soporte metÃƒÆ’Ã‚Â¡lico.",
        "/static/imagenes productos/premium_percussion.jpg",
        2720000.00,
        10,
    ),
    (
        "Ukelele Soprano",
        "Ukelele soprano tradicional en madera de acacia con cuerdas Aquila de alta calidad.",
        "/static/imagenes productos/premium_ukulele.jpg",
        480000.00,
        15,
    ),
]

CATALOGO_INSTRUMENTOS = CATALOGO_10_INSTRUMENTOS


# ============================================================================
# MODELO - BASE DE DATOS
# ============================================================================

def get_server_connection():
    """Conexión de servidor (sin base de datos seleccionada) solo para MySQL/MariaDB."""
    if USE_POSTGRES:
        return PgConnectionWrapper(PG_DSN)
    kwargs = {
        "host": DB_HOST,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "port": DB_PORT,
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": True,
    }
    if MYSQL_SSL:
        kwargs["ssl"] = {"ssl_mode": "REQUIRED"}
    return pymysql.connect(**kwargs)


def get_db_connection():
    """Devuelve una conexión activa: PostgreSQL > MySQL > SQLite."""
    global USE_SQLITE
    if USE_SQLITE:
        return SQLiteConnectionWrapper()
    if USE_POSTGRES:
        try:
            return PgConnectionWrapper(PG_DSN)
        except Exception as e:
            print(f"Aviso: PostgreSQL no disponible ({e}). Activando SQLite de emergencia.")
            USE_SQLITE = True
            return SQLiteConnectionWrapper()
    try:
        kwargs = {
            "host": DB_HOST,
            "user": DB_USER,
            "password": DB_PASSWORD,
            "database": DB_NAME,
            "port": DB_PORT,
            "charset": "utf8mb4",
            "cursorclass": DictCursor,
            "autocommit": True,
            "connect_timeout": 3,
        }
        if MYSQL_SSL:
            kwargs["ssl"] = {"ssl_mode": "REQUIRED"}
        return pymysql.connect(**kwargs)
    except Exception as e:
        print(f"Aviso: MySQL no disponible ({e}). Activando base de datos SQLite autónoma.")
        USE_SQLITE = True
        return SQLiteConnectionWrapper()


def escapar_identificador_mysql(nombre):
    return f"`{nombre.replace('`', '``')}`"

def migrar_datos_desde_sqlite(cursor):
    if not DATABASE.exists():
        return

    with sqlite3.connect(DATABASE) as sqlite_conn:
        sqlite_conn.row_factory = sqlite3.Row

        tabla_usuarios = sqlite_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'usuarios'"
        ).fetchone()
        if tabla_usuarios:
            usuarios = sqlite_conn.execute(
                """
                SELECT id, nombre_completo, correo, password_hash, rol, estado, fecha_registro
                FROM usuarios
                """
            ).fetchall()
            for usuario in usuarios:
                cursor.execute(
                    """
                    INSERT INTO usuarios
                        (id, nombre_completo, correo, password_hash, rol, estado, fecha_registro)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        nombre_completo = VALUES(nombre_completo),
                        password_hash = VALUES(password_hash),
                        rol = VALUES(rol),
                        estado = VALUES(estado)
                    """,
                    (
                        usuario["id"],
                        usuario["nombre_completo"],
                        usuario["correo"],
                        usuario["password_hash"],
                        usuario["rol"],
                        usuario["estado"],
                        usuario["fecha_registro"],
                    ),
                )

        tabla_productos = sqlite_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'productos'"
        ).fetchone()
        if tabla_productos:
            productos = sqlite_conn.execute(
                """
                SELECT id, nombre, descripcion, imagen_url, precio, stock, fecha_creacion
                FROM productos
                """
            ).fetchall()
            for producto in productos:
                cursor.execute(
                    """
                    INSERT INTO productos
                        (id, nombre, descripcion, imagen_url, precio, stock, fecha_creacion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        nombre = VALUES(nombre),
                        descripcion = VALUES(descripcion),
                        imagen_url = VALUES(imagen_url),
                        precio = VALUES(precio),
                        stock = VALUES(stock)
                    """,
                    (
                        producto["id"],
                        producto["nombre"],
                        producto["descripcion"],
                        producto["imagen_url"],
                        producto["precio"],
                        producto["stock"],
                        producto["fecha_creacion"],
                    ),
                )


def asegurar_columnas_usuarios(cursor):
    if USE_POSTGRES:
        # PostgreSQL: AFTER col no existe, usar solo ADD COLUMN IF NOT EXISTS
        columnas_pg = {
            "foto_perfil": "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS foto_perfil VARCHAR(500) NULL",
            "direccion_casa": "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS direccion_casa VARCHAR(255) NULL",
            "ciudad": "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ciudad VARCHAR(100) NULL",
            "codigo_postal": "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS codigo_postal VARCHAR(50) NULL",
            "tarjeta_enmascarada": "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS tarjeta_enmascarada VARCHAR(100) NULL",
            "metodo_pago_guardado": "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS metodo_pago_guardado VARCHAR(100) NULL",
        }
        for alter_sql in columnas_pg.values():
            cursor.execute(alter_sql)
        return

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
    if USE_POSTGRES:
        cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS descripcion TEXT NULL")
        cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS imagen_url VARCHAR(500) NULL")
        return

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
    if USE_POSTGRES:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
        cursor.execute("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS fecha_pedido TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
        return

    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'pedidos'
        """,
        (DB_NAME,),
    )
    columnas_actuales = {fila["COLUMN_NAME"] for fila in cursor.fetchall()}

    if "fecha_creacion" not in columnas_actuales and "fecha_pedido" in columnas_actuales:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
    elif "fecha_pedido" not in columnas_actuales and "fecha_creacion" in columnas_actuales:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN fecha_pedido TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")


def sembrar_catalogo_instrumentos(cursor):
    cursor.execute("SELECT nombre FROM productos")
    nombres_existentes = {fila["nombre"] for fila in cursor.fetchall()}
    productos_nuevos = [
        producto
        for producto in CATALOGO_INSTRUMENTOS
        if producto[0] not in nombres_existentes
    ]

    if productos_nuevos:
        cursor.executemany(
            """
            INSERT INTO productos (nombre, descripcion, imagen_url, precio, stock)
            VALUES (%s, %s, %s, %s, %s)
            """,
            productos_nuevos,
        )


def actualizar_imagenes_catalogo_instrumentos(cursor):
    cursor.executemany(
        """
        UPDATE productos
        SET imagen_url = %s
        WHERE nombre = %s
        """,
        [
            (imagen_url, nombre)
            for nombre, _descripcion, imagen_url, _precio, _stock in CATALOGO_INSTRUMENTOS
        ],
    )


ADMIN_INICIAL_CORREO = os.getenv("ADMIN_EMAIL", "admin@rock.com")
ADMIN_INICIAL_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin12345")


def asegurar_admin_inicial(cursor):
    cursor.execute(
        "SELECT id FROM usuarios WHERE rol = %s LIMIT 1",
        ("Administrador",),
    )
    if cursor.fetchone():
        return

    cursor.execute(
        """
        INSERT INTO usuarios (nombre_completo, correo, password_hash, rol, estado)
        VALUES (%s, %s, %s, 'Administrador', 'activo')
        ON DUPLICATE KEY UPDATE
            password_hash = VALUES(password_hash),
            rol = 'Administrador',
            estado = 'activo'
        """,
        (
            "Administrador Rock",
            ADMIN_INICIAL_CORREO,
            ADMIN_INICIAL_PASSWORD,
        ),
    )

def crear_indices_rendimiento(cursor):
    indices = [
        ("idx_productos_nombre", "CREATE INDEX idx_productos_nombre ON productos(nombre(50))"),
        ("idx_productos_precio", "CREATE INDEX idx_productos_precio ON productos(precio)"),
        ("idx_usuarios_correo", "CREATE INDEX idx_usuarios_correo ON usuarios(correo(50))"),
        ("idx_carrito_usuario", "CREATE INDEX idx_carrito_usuario ON carrito(usuario_id)"),
        ("idx_carrito_session", "CREATE INDEX idx_carrito_session ON carrito(session_key)"),
    ]
    for nombre_idx, create_sql in indices:
        try:
            cursor.execute(create_sql)
        except Exception:
            pass

def sembrar_10_productos(cursor):
    try:
        if USE_POSTGRES:
            cursor.execute("TRUNCATE TABLE productos RESTART IDENTITY CASCADE")
        else:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("TRUNCATE TABLE productos")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    except Exception:
        cursor.execute("DELETE FROM productos")

    for item in CATALOGO_10_INSTRUMENTOS:
        cursor.execute(
            """
            INSERT INTO productos (nombre, descripcion, imagen_url, precio, stock)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (nombre) DO UPDATE SET
                descripcion = EXCLUDED.descripcion,
                imagen_url = EXCLUDED.imagen_url,
                precio = EXCLUDED.precio,
                stock = EXCLUDED.stock
            """,
            item,
        )
    invalidador_cache_productos()

def init_db():
    global DB_INITIALIZED, USE_SQLITE

    if DB_INITIALIZED:
        return

    with DB_INIT_LOCK:
        if DB_INITIALIZED:
            return

        # --- PostgreSQL (Render) ---
        if USE_POSTGRES:
            try:
                conn = PgConnectionWrapper(PG_DSN)
                init_postgres_schema(conn, CATALOGO_10_INSTRUMENTOS, ADMIN_INICIAL_CORREO, ADMIN_INICIAL_PASSWORD)
                # Migración de datos y assets adicionales
                with conn.cursor() as cursor:
                    asegurar_columnas_usuarios(cursor)
                    asegurar_columnas_productos(cursor)
                    asegurar_columnas_pedidos(cursor)
                    cursor.execute(
                        "SELECT nombre FROM migraciones WHERE nombre = %s",
                        ("migracion_pesos_colombianos_cop_v2",),
                    )
                    if not cursor.fetchone():
                        sembrar_10_productos(cursor)
                        cursor.execute(
                            "INSERT INTO migraciones (nombre) VALUES (%s)",
                            ("migracion_pesos_colombianos_cop_v2",),
                        )
                conn.close()
                DB_INITIALIZED = True
                print("[DB] Conectado a PostgreSQL (Render) correctamente.")
                return
            except Exception as e:
                print(f"Error al inicializar PostgreSQL ({e}). Conmutando a SQLite de emergencia...")
                USE_SQLITE = True

        # --- MySQL local ---
        if not USE_SQLITE:
            try:
                try:
                    with get_server_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute(
                                f"CREATE DATABASE IF NOT EXISTS {escapar_identificador_mysql(DB_NAME)} "
                                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                            )
                except Exception:
                    pass

                with get_db_connection() as conn:
                    if isinstance(conn, SQLiteConnectionWrapper):
                        USE_SQLITE = True
                    else:
                        with conn.cursor() as cursor:
                            cursor.execute(CREATE_TABLE_USUARIOS)
                            cursor.execute(CREATE_TABLE_PRODUCTOS)
                            cursor.execute(CREATE_TABLE_CARRITO)
                            cursor.execute(CREATE_TABLE_MIGRACIONES)
                            cursor.execute(CREATE_TABLE_PEDIDOS)
                            cursor.execute(CREATE_TABLE_PEDIDO_DETALLES)
                            asegurar_columnas_usuarios(cursor)
                            asegurar_columnas_productos(cursor)
                            asegurar_columnas_pedidos(cursor)
                            asegurar_admin_inicial(cursor)
                            crear_indices_rendimiento(cursor)
                            cursor.execute(
                                "SELECT nombre FROM migraciones WHERE nombre = %s",
                                ("migracion_pesos_colombianos_cop_v2",),
                            )
                            cat_10 = cursor.fetchone()
                            if not cat_10:
                                sembrar_10_productos(cursor)
                                cursor.execute(
                                    "INSERT INTO migraciones (nombre) VALUES (%s)",
                                    ("migracion_pesos_colombianos_cop_v2",),
                                )
                        DB_INITIALIZED = True
                        return
            except Exception as e:
                print(f"Error al inicializar MySQL ({e}). Conmutando automáticamente a SQLite integrado...")
                USE_SQLITE = True

        # --- SQLite (fallback) ---
        if USE_SQLITE:
            try:
                conn = SQLiteConnectionWrapper()
                init_sqlite_schema(conn, CATALOGO_10_INSTRUMENTOS, ADMIN_INICIAL_CORREO, ADMIN_INICIAL_PASSWORD)
                DB_INITIALIZED = True
                print("[DB] Usando SQLite local (fallback).")
            except Exception as err_lite:
                print(f"Error al inicializar SQLite: {err_lite}")


# ============================================================================
# MODELO - CONSULTAS Y REPOSITORIOS
# ============================================================================

def obtener_usuarios_admin():
    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre_completo, correo, estado
                FROM usuarios
                ORDER BY fecha_registro DESC, id DESC
                """
            )
            filas = cursor.fetchall()

    return [
        {
            "id": fila["id"],
            "nombre": fila["nombre_completo"],
            "email": fila["correo"],
            "estado": "Activo" if fila["estado"] == "activo" else "Reportado",
            "compras": "Permitidas" if fila["estado"] == "activo" else "Bloqueadas",
        }
        for fila in filas
    ]


import time

PRODUCTOS_CACHE = None
PRODUCTOS_CACHE_TIME = 0
CACHE_TTL_SEGUNDOS = 30

def invalidador_cache_productos():
    global PRODUCTOS_CACHE, PRODUCTOS_CACHE_TIME
    PRODUCTOS_CACHE = None
    PRODUCTOS_CACHE_TIME = 0

def obtener_productos():
    global PRODUCTOS_CACHE, PRODUCTOS_CACHE_TIME
    ahora = time.time()
    if PRODUCTOS_CACHE is not None and (ahora - PRODUCTOS_CACHE_TIME) < CACHE_TTL_SEGUNDOS:
        return PRODUCTOS_CACHE

    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre, descripcion, imagen_url, precio, stock
                FROM productos
                ORDER BY id DESC
                """
            )
            PRODUCTOS_CACHE = cursor.fetchall()
            PRODUCTOS_CACHE_TIME = ahora
            return PRODUCTOS_CACHE


def obtener_categorias_tienda():
    return [
        {
            "slug": "cuerdas",
            "nombre": "Cuerdas",
            "descripcion": "Guitarras, bajos, ukeleles, mandolinas, banjos y arpas.",
            "imagen": "/static/imagenes productos/premium_guitar.jpg",
            "opciones": ["Guitarra", "Bajo", "Ukelele", "Mandolina", "Banjo", "Arpa"],
            "palabras": ["guitarra", "bajo", "ukelele", "mandolina", "banjo", "arpa"],
        },
        {
            "slug": "cuerdas-frotadas",
            "nombre": "Cuerdas frotadas",
            "descripcion": "Violines, violas, violonchelos y contrabajos para estudio y concierto.",
            "imagen": "/static/imagenes productos/premium_violin.jpg",
            "opciones": ["Violin", "Viola", "Violonchelo", "Contrabajo"],
            "palabras": ["violin", "viola", "violonchelo", "contrabajo"],
        },
        {
            "slug": "teclados",
            "nombre": "Teclados",
            "descripcion": "Pianos digitales, sintetizadores, arrangers y controladores MIDI.",
            "imagen": "/static/imagenes productos/premium_piano.jpg",
            "opciones": ["Piano", "Teclado", "Sintetizador", "MIDI", "Acordeon", "Melodica"],
            "palabras": ["piano", "teclado", "sintetizador", "midi", "acordeon", "melodica"],
        },
        {
            "slug": "percusion",
            "nombre": "Percusion",
            "descripcion": "Baterias, cajas, bombos, cajones, djembes y percusion menor.",
            "imagen": "/static/imagenes productos/premium_drums.jpg",
            "opciones": ["Bateria", "Caja", "Bombo", "Cajon", "Djembe", "Maracas"],
            "palabras": ["bateria", "caja", "bombo", "cajon", "djembe", "maracas", "pandereta", "triangulo", "tambor"],
        },
        {
            "slug": "vientos-madera",
            "nombre": "Vientos madera",
            "descripcion": "Flautas, clarinetes, saxofones, oboes y fagotes.",
            "imagen": "/static/imagenes productos/premium_woodwind.jpg",
            "opciones": ["Flauta", "Clarinete", "Saxofon", "Oboe", "Fagot"],
            "palabras": ["flauta", "clarinete", "saxofon", "oboe", "fagot"],
        },
        {
            "slug": "vientos-metal",
            "nombre": "Vientos metal",
            "descripcion": "Trompetas, trombones, cornos, tubas y eufonios.",
            "imagen": "/static/imagenes productos/premium_brass.jpg",
            "opciones": ["Trompeta", "Trombon", "Corno", "Tuba", "Eufonio"],
            "palabras": ["trompeta", "trombon", "corno", "tuba", "eufonio"],
        },
        {
            "slug": "tradicionales",
            "nombre": "Tradicionales",
            "descripcion": "Cuatro llanero, tiple, charango y otros sonidos de raiz.",
            "imagen": "/static/imagenes productos/premium_ukulele.jpg",
            "opciones": ["Cuatro", "Tiple", "Charango"],
            "palabras": ["cuatro", "tiple", "charango"],
        },
        {
            "slug": "percusion-latina",
            "nombre": "Percusion latina",
            "descripcion": "Congas, bongos, timbales y piezas para ritmos latinos.",
            "imagen": "/static/imagenes productos/premium_percussion.jpg",
            "opciones": ["Congas", "Bongos", "Timbal"],
            "palabras": ["congas", "bongos", "timbal"],
        },
    ]


def filtrar_productos_tienda(productos, categoria_slug="", busqueda=""):
    categorias_por_slug = {
        categoria["slug"]: categoria
        for categoria in obtener_categorias_tienda()
    }
    categoria = categorias_por_slug.get(categoria_slug)
    texto_busqueda = busqueda.lower()

    productos_filtrados = []
    for producto in productos:
        texto_producto = f"{producto['nombre']} {producto.get('descripcion') or ''}".lower()
        if categoria and not any(palabra in texto_producto for palabra in categoria["palabras"]):
            continue
        if texto_busqueda and texto_busqueda not in texto_producto:
            continue
        productos_filtrados.append(producto)

    return productos_filtrados


def obtener_producto_por_id(producto_id):
    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre, descripcion, imagen_url, precio, stock
                FROM productos
                WHERE id = %s
                """,
                (producto_id,),
            )
            return cursor.fetchone()


def obtener_usuario_admin_por_id(usuario_id):
    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre_completo, correo, rol, estado
                FROM usuarios
                WHERE id = %s
                """,
                (usuario_id,),
            )
            return cursor.fetchone()


# ============================================================================
# MODELO - CARRITO
# ============================================================================

def obtener_session_carrito():
    if "carrito_session_key" not in session:
        session["carrito_session_key"] = uuid4().hex
    return session["carrito_session_key"]


def obtener_total_carrito():
    init_db()
    usuario_id = session.get("usuario_id")
    session_key = session.get("carrito_session_key")

    if not usuario_id and not session_key:
        return 0

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            if usuario_id:
                cursor.execute(
                    "SELECT COALESCE(SUM(cantidad), 0) AS total FROM carrito WHERE usuario_id = %s",
                    (usuario_id,),
                )
            else:
                cursor.execute(
                    "SELECT COALESCE(SUM(cantidad), 0) AS total FROM carrito WHERE session_key = %s",
                    (session_key,),
                )
            return cursor.fetchone()["total"]


def obtener_items_carrito():
    init_db()
    usuario_id = session.get("usuario_id")
    session_key = session.get("carrito_session_key")

    if not usuario_id and not session_key:
        return [], 0

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            consulta = """
                SELECT
                    c.id,
                    c.producto_id,
                    c.cantidad,
                    p.nombre,
                    p.descripcion,
                    p.imagen_url,
                    p.precio,
                    p.stock,
                    (p.precio * c.cantidad) AS subtotal
                FROM carrito c
                INNER JOIN productos p ON p.id = c.producto_id
                WHERE {condicion}
                ORDER BY c.fecha_actualizado DESC, c.id DESC
            """

            if usuario_id:
                cursor.execute(consulta.format(condicion="c.usuario_id = %s"), (usuario_id,))
            else:
                cursor.execute(consulta.format(condicion="c.session_key = %s"), (session_key,))

            items = cursor.fetchall()

    total = sum(item["subtotal"] for item in items)
    return items, total


def agregar_producto_carrito(producto_id):
    init_db()
    usuario_id = session.get("usuario_id")
    session_key = None if usuario_id else obtener_session_carrito()

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, nombre, stock FROM productos WHERE id = %s", (producto_id,))
            producto = cursor.fetchone()

            if not producto:
                return None

            if producto["stock"] <= 0:
                producto["sin_stock"] = True
                return producto

            if usuario_id:
                cursor.execute(
                    "SELECT id, cantidad FROM carrito WHERE usuario_id = %s AND producto_id = %s",
                    (usuario_id, producto_id),
                )
                item_existente = cursor.fetchone()
                if item_existente:
                    nueva_cantidad = min(item_existente["cantidad"] + 1, producto["stock"])
                    cursor.execute(
                        "UPDATE carrito SET cantidad = %s WHERE id = %s",
                        (nueva_cantidad, item_existente["id"]),
                    )
                    producto["cantidad"] = nueva_cantidad
                    producto["limite_stock"] = nueva_cantidad == item_existente["cantidad"]
                    return producto

                cursor.execute(
                    """
                    INSERT INTO carrito (usuario_id, producto_id, cantidad)
                    VALUES (%s, %s, 1)
                    """,
                    (usuario_id, producto_id),
                )
            else:
                cursor.execute(
                    "SELECT id, cantidad FROM carrito WHERE session_key = %s AND producto_id = %s",
                    (session_key, producto_id),
                )
                item_existente = cursor.fetchone()
                if item_existente:
                    nueva_cantidad = min(item_existente["cantidad"] + 1, producto["stock"])
                    cursor.execute(
                        "UPDATE carrito SET cantidad = %s WHERE id = %s",
                        (nueva_cantidad, item_existente["id"]),
                    )
                    producto["cantidad"] = nueva_cantidad
                    producto["limite_stock"] = nueva_cantidad == item_existente["cantidad"]
                    return producto

                cursor.execute(
                    """
                    INSERT INTO carrito (session_key, producto_id, cantidad)
                    VALUES (%s, %s, 1)
                    """,
                    (session_key, producto_id),
                )

            producto["cantidad"] = 1
            producto["limite_stock"] = False
            return producto


def obtener_condicion_carrito_actual():
    usuario_id = session.get("usuario_id")
    session_key = session.get("carrito_session_key")

    if usuario_id:
        return "usuario_id = %s", usuario_id
    if session_key:
        return "session_key = %s", session_key
    return None, None


def actualizar_item_carrito(item_id, cantidad):
    init_db()
    condicion, valor = obtener_condicion_carrito_actual()
    if not condicion:
        return False, "Tu carrito esta vacio."

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT c.id, p.nombre, p.stock
                FROM carrito c
                INNER JOIN productos p ON p.id = c.producto_id
                WHERE c.id = %s AND c.{condicion}
                """,
                (item_id, valor),
            )
            item = cursor.fetchone()

            if not item:
                return False, "El producto no esta en tu carrito."

            if cantidad <= 0:
                cursor.execute("DELETE FROM carrito WHERE id = %s", (item_id,))
                return True, f"{item['nombre']} eliminado del carrito."

            cantidad_final = min(cantidad, item["stock"])
            if cantidad_final <= 0:
                cursor.execute("DELETE FROM carrito WHERE id = %s", (item_id,))
                return True, f"{item['nombre']} ya no tiene stock y fue retirado."

            cursor.execute(
                "UPDATE carrito SET cantidad = %s WHERE id = %s",
                (cantidad_final, item_id),
            )

    if cantidad_final < cantidad:
        return True, f"Solo hay {cantidad_final} unidad(es) disponibles de {item['nombre']}."
    return True, f"Cantidad de {item['nombre']} actualizada."


def eliminar_item_carrito(item_id):
    init_db()
    condicion, valor = obtener_condicion_carrito_actual()
    if not condicion:
        return False

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"DELETE FROM carrito WHERE id = %s AND {condicion}",
                (item_id, valor),
            )
            return cursor.rowcount > 0


def vaciar_carrito_actual():
    init_db()
    condicion, valor = obtener_condicion_carrito_actual()
    if not condicion:
        return

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"DELETE FROM carrito WHERE {condicion}", (valor,))


def finalizar_compra_actual():
    init_db()
    condicion, valor = obtener_condicion_carrito_actual()
    if not condicion:
        return False, "Tu carrito esta vacio."

    with get_db_connection() as conn:
        try:
            conn.begin()
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT c.id, c.cantidad, c.producto_id, p.nombre, p.stock
                    FROM carrito c
                    INNER JOIN productos p ON p.id = c.producto_id
                    WHERE c.{condicion}
                    FOR UPDATE
                    """,
                    (valor,),
                )
                items = cursor.fetchall()

                if not items:
                    conn.rollback()
                    return False, "Tu carrito esta vacio."

                sin_stock = [
                    item
                    for item in items
                    if item["stock"] <= 0 or item["cantidad"] > item["stock"]
                ]
                if sin_stock:
                    conn.rollback()
                    nombres = ", ".join(item["nombre"] for item in sin_stock[:3])
                    return False, f"Revisa stock antes de pagar: {nombres}."

                for item in items:
                    cursor.execute(
                        """
                        UPDATE productos
                        SET stock = stock - %s
                        WHERE id = %s
                        """,
                        (item["cantidad"], item["producto_id"]),
                    )

                cursor.execute(f"DELETE FROM carrito WHERE {condicion}", (valor,))

            conn.commit()
            return True, "Compra finalizada. Gracias por confiar en Rock Corporation."
        except Exception:
            conn.rollback()
            raise


def fusionar_carrito_invitado(usuario_id):
    session_key = session.get("carrito_session_key")
    if not session_key:
        return

    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT producto_id, cantidad
                FROM carrito
                WHERE session_key = %s
                """,
                (session_key,),
            )
            items_invitado = cursor.fetchall()

            for item in items_invitado:
                if USE_POSTGRES:
                    cursor.execute(
                        """
                        INSERT INTO carrito (usuario_id, producto_id, cantidad)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (usuario_id, producto_id)
                        DO UPDATE SET cantidad = carrito.cantidad + EXCLUDED.cantidad
                        """,
                        (usuario_id, item["producto_id"], item["cantidad"]),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO carrito (usuario_id, producto_id, cantidad)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE cantidad = cantidad + VALUES(cantidad)
                        """,
                        (usuario_id, item["producto_id"], item["cantidad"]),
                    )

            cursor.execute("DELETE FROM carrito WHERE session_key = %s", (session_key,))

    session.pop("carrito_session_key", None)


class UsuarioModelo:
    listar_admin = staticmethod(obtener_usuarios_admin)
    obtener_admin_por_id = staticmethod(obtener_usuario_admin_por_id)


class ProductoModelo:
    listar = staticmethod(obtener_productos)
    obtener_por_id = staticmethod(obtener_producto_por_id)
    categorias = staticmethod(obtener_categorias_tienda)
    filtrar_tienda = staticmethod(filtrar_productos_tienda)


class CarritoModelo:
    obtener_total = staticmethod(obtener_total_carrito)
    obtener_items = staticmethod(obtener_items_carrito)
    agregar_producto = staticmethod(agregar_producto_carrito)
    actualizar_item = staticmethod(actualizar_item_carrito)
    eliminar_item = staticmethod(eliminar_item_carrito)
    vaciar_actual = staticmethod(vaciar_carrito_actual)
    finalizar_compra = staticmethod(finalizar_compra_actual)
    fusionar_invitado = staticmethod(fusionar_carrito_invitado)


class BaseDatosModelo:
    inicializar = staticmethod(init_db)
    conexion = staticmethod(get_db_connection)


def crear_pedido_nuevo(usuario_id, nombre_cliente, correo_cliente, direccion, ciudad, codigo_postal, metodo_pago):
    init_db()
    items, total = obtener_items_carrito()
    if not items:
        return None, "El carrito esta vacio."

    with get_db_connection() as conn:
        try:
            conn.begin()
            with conn.cursor() as cursor:
                # 1. Verificar stock
                for item in items:
                    cursor.execute(
                        "SELECT stock, nombre FROM productos WHERE id = %s FOR UPDATE",
                        (item["producto_id"],),
                    )
                    prod = cursor.fetchone()
                    if not prod or prod["stock"] < item["cantidad"]:
                        conn.rollback()
                        nombre_prod = prod["nombre"] if prod else "un producto"
                        return None, f"No hay suficiente stock para {nombre_prod}."

                # 2. Insertar pedido
                if USE_POSTGRES:
                    cursor.execute(
                        """
                        INSERT INTO pedidos 
                            (usuario_id, nombre_cliente, correo_cliente, direccion, ciudad, codigo_postal, total, metodo_pago, estado)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pagado')
                        RETURNING id
                        """,
                        (usuario_id, nombre_cliente, correo_cliente, direccion, ciudad, codigo_postal, total, metodo_pago),
                    )
                    row = cursor.fetchone()
                    pedido_id = row["id"] if row else None
                else:
                    cursor.execute(
                        """
                        INSERT INTO pedidos 
                            (usuario_id, nombre_cliente, correo_cliente, direccion, ciudad, codigo_postal, total, metodo_pago, estado)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pagado')
                        """,
                        (usuario_id, nombre_cliente, correo_cliente, direccion, ciudad, codigo_postal, total, metodo_pago),
                    )
                    pedido_id = cursor.lastrowid

                # 3. Insertar detalles y actualizar stock
                for item in items:
                    cursor.execute(
                        """
                        INSERT INTO pedido_detalles 
                            (pedido_id, producto_id, cantidad, precio_unitario)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (pedido_id, item["producto_id"], item["cantidad"], item["precio"]),
                    )
                    cursor.execute(
                        """
                        UPDATE productos 
                        SET stock = stock - %s 
                        WHERE id = %s
                        """,
                        (item["cantidad"], item["producto_id"]),
                    )

            conn.commit()
            vaciar_carrito_actual()
            return pedido_id, "Compra finalizada con ÃƒÆ’Ã‚Â©xito."
        except Exception as e:
            conn.rollback()
            return None, f"Error al procesar la compra: {str(e)}"


def obtener_pedido_por_id(pedido_id):
    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM pedidos WHERE id = %s",
                (pedido_id,),
            )
            return cursor.fetchone()


def obtener_detalles_pedido(pedido_id):
    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT pd.*, p.nombre, p.imagen_url 
                FROM pedido_detalles pd
                JOIN productos p ON pd.producto_id = p.id
                WHERE pd.pedido_id = %s
                """,
                (pedido_id,),
            )
            return cursor.fetchall()


def obtener_pedidos_usuario(usuario_id):
    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT *, COALESCE(fecha_creacion, fecha_pedido, CURRENT_TIMESTAMP) AS fecha_display FROM pedidos WHERE usuario_id = %s ORDER BY id DESC",
                (usuario_id,),
            )
            return cursor.fetchall()


def obtener_todos_los_pedidos():
    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT *, COALESCE(fecha_creacion, fecha_pedido, CURRENT_TIMESTAMP) AS fecha_display FROM pedidos ORDER BY id DESC",
            )
            return cursor.fetchall()


def actualizar_estado_pedido(pedido_id, nuevo_estado):
    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE pedidos SET estado = %s WHERE id = %s",
                (nuevo_estado, pedido_id),
            )


class PedidoModelo:
    crear = staticmethod(crear_pedido_nuevo)
    obtener_por_id = staticmethod(obtener_pedido_por_id)
    obtener_detalles = staticmethod(obtener_detalles_pedido)
    obtener_por_usuario = staticmethod(obtener_pedidos_usuario)
    obtener_todos = staticmethod(obtener_todos_los_pedidos)
    actualizar_estado = staticmethod(actualizar_estado_pedido)


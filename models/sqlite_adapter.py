"""
Adaptador de Base de Datos SQLite para ROCK CORPORATION.
Permite que la aplicación funcione de forma autónoma (Zero-Config)
sin necesidad de un servidor MySQL externo cuando este no esté disponible.
"""

import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_DB_PATH = BASE_DIR / "rock_corporation.db"


class SQLiteDictCursor:
    def __init__(self, conn, real_cursor):
        self._conn = conn
        self._cursor = real_cursor

    def _convert_query(self, query):
        q = query
        # Eliminar cláusulas incompatibles como FOR UPDATE
        q = re.sub(r'\s+FOR\s+UPDATE\b', '', q, flags=re.IGNORECASE)
        # Convertir placeholders de MySQL (%s) a SQLite (?)
        # Solo aquellos %s que no sean parte de literales como %
        q = re.sub(r'(?<!%)%s', '?', q)
        # Convertir ON DUPLICATE KEY UPDATE a ON CONFLICT DO UPDATE
        if 'ON DUPLICATE KEY UPDATE' in q.upper():
            q = re.sub(r'ON\s+DUPLICATE\s+KEY\s+UPDATE', 'ON CONFLICT DO UPDATE SET', q, flags=re.IGNORECASE)
            q = re.sub(r'VALUES\((\w+)\)', r'excluded.\1', q, flags=re.IGNORECASE)
        return q

    def execute(self, query, params=None):
        q = self._convert_query(query)
        try:
            if params is None:
                return self._cursor.execute(q)
            return self._cursor.execute(q, params)
        except Exception as e:
            # Fallback tolerante para diferencias menores de sintaxis
            raise e

    def executemany(self, query, seq_of_params):
        q = self._convert_query(query)
        return self._cursor.executemany(q, seq_of_params)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        return [dict(row) for row in self._cursor.fetchall()]

    def fetchmany(self, size=None):
        if size is None:
            rows = self._cursor.fetchmany()
        else:
            rows = self._cursor.fetchmany(size)
        return [dict(row) for row in rows]

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    def close(self):
        try:
            self._cursor.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class SQLiteConnectionWrapper:
    def __init__(self, db_path=SQLITE_DB_PATH):
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30.0)
        self._conn.row_factory = sqlite3.Row
        self._init_functions()

    def _init_functions(self):
        c = self._conn
        c.create_function("NOW", 0, lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        c.create_function("CURDATE", 0, lambda: datetime.now().strftime("%Y-%m-%d"))
        c.create_function("MONTH", 1, lambda val: int(str(val)[:10].split("-")[1]) if val else 1)
        c.create_function("YEAR", 1, lambda val: int(str(val)[:4]) if val else 2026)
        c.create_function("CONCAT", -1, lambda *args: "".join(str(a) for a in args if a is not None))
        c.create_function("IFNULL", 2, lambda a, b: b if a is None else a)

        def fn_timestampdiff(unit, d1, d2):
            try:
                dt1 = datetime.fromisoformat(str(d1).replace(" ", "T"))
                dt2 = datetime.fromisoformat(str(d2).replace(" ", "T"))
                diff = (dt2 - dt1).total_seconds()
                u = str(unit).upper()
                if "MIN" in u:
                    return int(diff // 60)
                elif "HOUR" in u:
                    return int(diff // 3600)
                elif "DAY" in u:
                    return int(diff // 86400)
                return int(diff)
            except Exception:
                return 0

        c.create_function("TIMESTAMPDIFF", 3, fn_timestampdiff)

    def cursor(self):
        return SQLiteDictCursor(self._conn, self._conn.cursor())

    def begin(self):
        pass

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()


def init_sqlite_schema(conn, catalogo_10, admin_correo, admin_password):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_completo TEXT NOT NULL,
                correo TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                rol TEXT NOT NULL,
                foto_perfil TEXT NULL,
                fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                estado TEXT NOT NULL DEFAULT 'activo'
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                descripcion TEXT NULL,
                imagen_url TEXT NULL,
                precio REAL NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS carrito (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NULL,
                session_key TEXT NULL,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 1,
                fecha_agregado TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizado TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(usuario_id, producto_id),
                UNIQUE(session_key, producto_id),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS migraciones (
                nombre TEXT PRIMARY KEY,
                fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NULL,
                nombre_cliente TEXT NOT NULL,
                correo_cliente TEXT NOT NULL,
                direccion TEXT NOT NULL,
                ciudad TEXT NOT NULL,
                codigo_postal TEXT NOT NULL,
                total REAL NOT NULL,
                metodo_pago TEXT NOT NULL,
                estado TEXT NOT NULL DEFAULT 'Pagado',
                fecha_pedido TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pedido_detalles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 1,
                precio_unitario REAL NOT NULL,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
            );
            """
        )

        # Sembrar admin inicial
        cur.execute("SELECT id FROM usuarios WHERE correo = ? LIMIT 1", (admin_correo,))
        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO usuarios (nombre_completo, correo, password_hash, rol, estado)
                VALUES (?, ?, ?, 'Administrador', 'activo')
                """,
                ("Administrador Rock", admin_correo, admin_password),
            )

        # Sembrar productos
        cur.execute("SELECT COUNT(*) AS total FROM productos")
        fila = cur.fetchone()
        if not fila or fila.get("total", 0) == 0:
            for item in catalogo_10:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO productos (nombre, descripcion, imagen_url, precio, stock)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    item,
                )
    conn.commit()

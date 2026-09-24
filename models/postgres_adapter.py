"""
Adaptador PostgreSQL para ROCK CORPORATION.
Envuelve psycopg2 con una interfaz compatible con pymysql (DictCursor, autocommit, context manager).
Permite que models.py funcione sin cambios con PostgreSQL de Render.
"""

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None


class PgDictCursor:
    """Cursor que devuelve filas como diccionarios, compatible con pymysql.DictCursor."""

    def __init__(self, real_cursor):
        self._cursor = real_cursor

    def execute(self, query, params=None):
        # psycopg2 usa %s igual que pymysql ✓
        # Adaptar ON DUPLICATE KEY UPDATE → INSERT ... ON CONFLICT DO UPDATE
        query = _adapt_pg_query(query)
        if params is None:
            return self._cursor.execute(query)
        return self._cursor.execute(query, params)

    def executemany(self, query, seq_of_params):
        query = _adapt_pg_query(query)
        return self._cursor.executemany(query, seq_of_params)

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
        # En PostgreSQL se usa RETURNING id explícitamente en models.py.
        # Esta propiedad es un fallback para compatibilidad; devuelve None si no se usó RETURNING.
        return None

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


class PgConnectionWrapper:
    """
    Conexión PostgreSQL compatible con el patrón de uso de pymysql en models.py:
    - context manager (__enter__ / __exit__)
    - .cursor() devuelve PgDictCursor
    - .begin() / .commit() / .rollback()
    """

    def __init__(self, dsn: str):
        if psycopg2 is None:
            raise RuntimeError("psycopg2 is not installed. Por favor, instálalo con 'pip install psycopg2-binary' para usar PostgreSQL.")
        self._conn = psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)
        self._conn.autocommit = True  # igual que pymysql con autocommit=True

    def cursor(self):
        return PgDictCursor(self._conn.cursor())

    def begin(self):
        """Inicia una transacción desactivando autocommit temporalmente."""
        self._conn.autocommit = False

    def commit(self):
        self._conn.commit()
        self._conn.autocommit = True

    def rollback(self):
        self._conn.rollback()
        self._conn.autocommit = True

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            try:
                self.rollback()
            except Exception:
                pass
        self.close()


# ---------------------------------------------------------------------------
# Adaptación de sintaxis MySQL → PostgreSQL
# ---------------------------------------------------------------------------

import re


def _adapt_pg_query(query: str) -> str:
    """Convierte construcciones MySQL a PostgreSQL equivalentes."""
    q = query

    # SET FOREIGN_KEY_CHECKS → ignorar (PostgreSQL no lo necesita)
    if re.search(r'SET\s+FOREIGN_KEY_CHECKS', q, re.IGNORECASE):
        return "SELECT 1"  # no-op

    # TRUNCATE → compatible (mismo en PG)

    # ENGINE=InnoDB, CHARSET=... → eliminar
    q = re.sub(r'\s*ENGINE\s*=\s*\w+', '', q, flags=re.IGNORECASE)
    q = re.sub(r'\s*DEFAULT\s+CHARSET\s*=\s*\w+', '', q, flags=re.IGNORECASE)
    q = re.sub(r'\s*COLLATE\s*=?\s*[\w_]+', '', q, flags=re.IGNORECASE)
    q = re.sub(r'\s*CHARACTER\s+SET\s+\w+', '', q, flags=re.IGNORECASE)
    q = re.sub(r'\s*COLLATE\s+[\w_]+', '', q, flags=re.IGNORECASE)

    # AUTO_INCREMENT → SERIAL / se maneja via SERIAL en CREATE TABLE
    # En ALTER TABLE no es necesario

    # INFORMATION_SCHEMA.COLUMNS (MySQL) → information_schema.columns (PG, mismo nombre, lowercase)
    # PG lo acepta igual ✓, pero TABLE_SCHEMA → table_catalog o table_schema
    # Ajustar: WHERE TABLE_SCHEMA = %s → WHERE table_schema = 'public' AND table_catalog = current_database()
    q = re.sub(
        r'WHERE\s+TABLE_SCHEMA\s*=\s*%s\s+AND\s+TABLE_NAME\s*=\s*%s',
        "WHERE table_schema = 'public' AND table_name = %s",
        q,
        flags=re.IGNORECASE,
    )
    q = re.sub(
        r'WHERE\s+TABLE_SCHEMA\s*=\s*%s\s+AND\s+TABLE_NAME\s*=\s*[\'\"]([\w]+)[\'\"]',
        r"WHERE table_schema = 'public' AND table_name = '\1'",
        q,
        flags=re.IGNORECASE,
    )
    # Columna COLUMN_NAME → column_name (PG lowercase)
    q = q.replace('COLUMN_NAME', 'column_name')
    q = q.replace('TABLE_NAME', 'table_name')
    q = q.replace('TABLE_SCHEMA', 'table_schema')

    # ON DUPLICATE KEY UPDATE → INSERT ... ON CONFLICT DO UPDATE SET
    if 'ON DUPLICATE KEY UPDATE' in q.upper():
        q = re.sub(
            r'ON\s+DUPLICATE\s+KEY\s+UPDATE',
            'ON CONFLICT DO UPDATE SET',
            q,
            flags=re.IGNORECASE,
        )
        # VALUES(col) → EXCLUDED.col
        q = re.sub(r'VALUES\s*\(\s*(\w+)\s*\)', r'EXCLUDED.\1', q, flags=re.IGNORECASE)
        # cantidad = cantidad + VALUES(cantidad) → cantidad = carrito.cantidad + EXCLUDED.cantidad
        # (ya manejado por el regex anterior si es simple)

    # ENUM(...) → TEXT (PostgreSQL no tiene ENUM inline igual)
    q = re.sub(r"ENUM\s*\([^)]+\)", "TEXT", q, flags=re.IGNORECASE)

    # INT AUTO_INCREMENT → SERIAL
    q = re.sub(r'\bINT\s+AUTO_INCREMENT\b', 'SERIAL', q, flags=re.IGNORECASE)
    q = re.sub(r'\bINTEGER\s+AUTO_INCREMENT\b', 'SERIAL', q, flags=re.IGNORECASE)

    # UNIQUE KEY nombre (col1, col2) → UNIQUE (col1, col2)
    q = re.sub(r'\bUNIQUE\s+KEY\s+\w+\s*\(', 'UNIQUE (', q, flags=re.IGNORECASE)

    # KEY nombre (col) → (ignorar índices dentro de CREATE TABLE)
    q = re.sub(r',\s*KEY\s+\w+\s*\([^)]+\)', '', q, flags=re.IGNORECASE)

    # CONSTRAINT nombre FOREIGN KEY → CONSTRAINT nombre FOREIGN KEY (PG lo acepta ✓)

    # VARCHAR(n) → VARCHAR(n) ✓, DECIMAL → NUMERIC ✓ (PG acepta DECIMAL también)

    # CURRENT_TIMESTAMP → CURRENT_TIMESTAMP ✓

    # utf8mb4 → eliminar (ya manejado arriba)

    # backtick identifiers → comillas dobles PG
    q = re.sub(r'`([^`]+)`', r'"\1"', q)

    # FOR UPDATE → compatible en PG ✓

    return q


def init_postgres_schema(conn, catalogo_10, admin_correo, admin_password):
    """Crea todas las tablas en PostgreSQL si no existen."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nombre_completo VARCHAR(150) NOT NULL,
                correo VARCHAR(150) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                rol VARCHAR(50) NOT NULL DEFAULT 'Cliente',
                foto_perfil VARCHAR(500) NULL,
                fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                estado VARCHAR(20) NOT NULL DEFAULT 'activo',
                direccion_casa VARCHAR(255) NULL,
                ciudad VARCHAR(100) NULL,
                codigo_postal VARCHAR(50) NULL,
                tarjeta_enmascarada VARCHAR(100) NULL,
                metodo_pago_guardado VARCHAR(100) NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(150) NOT NULL UNIQUE,
                descripcion TEXT NULL,
                imagen_url VARCHAR(500) NULL,
                precio NUMERIC(10,2) NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS carrito (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NULL,
                session_key VARCHAR(120) NULL,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 1,
                fecha_agregado TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizado TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (usuario_id, producto_id),
                UNIQUE (session_key, producto_id),
                CONSTRAINT fk_carrito_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                CONSTRAINT fk_carrito_producto FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS migraciones (
                nombre VARCHAR(80) PRIMARY KEY,
                fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NULL,
                nombre_cliente VARCHAR(150) NOT NULL,
                correo_cliente VARCHAR(150) NOT NULL,
                direccion VARCHAR(255) NOT NULL,
                ciudad VARCHAR(100) NOT NULL,
                codigo_postal VARCHAR(50) NOT NULL,
                total NUMERIC(10,2) NOT NULL,
                metodo_pago VARCHAR(100) NOT NULL DEFAULT 'Tarjeta de Crédito',
                estado VARCHAR(50) NOT NULL DEFAULT 'Pagado',
                fecha_pedido TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_pedidos_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pedido_detalles (
                id SERIAL PRIMARY KEY,
                pedido_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 1,
                precio_unitario NUMERIC(10,2) NOT NULL,
                CONSTRAINT fk_detalles_pedido FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
                CONSTRAINT fk_detalles_producto FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
            )
        """)

        # Admin inicial
        cur.execute("SELECT id FROM usuarios WHERE correo = %s LIMIT 1", (admin_correo,))
        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO usuarios (nombre_completo, correo, password_hash, rol, estado)
                VALUES (%s, %s, %s, 'Administrador', 'activo')
                """,
                ("Administrador Rock", admin_correo, admin_password),
            )

        # Productos iniciales
        cur.execute("SELECT COUNT(*) AS total FROM productos")
        fila = cur.fetchone()
        conteo = 0
        if fila:
            conteo = fila.get("total") or fila.get("count") or 0
        if conteo == 0:
            for item in catalogo_10:
                cur.execute(
                    """
                    INSERT INTO productos (nombre, descripcion, imagen_url, precio, stock)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (nombre) DO NOTHING
                    """,
                    item,
                )

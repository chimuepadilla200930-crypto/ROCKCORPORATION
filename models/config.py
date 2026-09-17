import os
from pathlib import Path


# ============================================================================
# CONFIGURACION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno desde .env si existe
env_path = BASE_DIR / ".env"
if env_path.exists():
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip("'\"")
    except Exception as e:
        print(f"Advertencia al cargar .env: {e}")

DATABASE = BASE_DIR / "lycaon_registro.db"
PRODUCT_IMAGES_FOLDER = BASE_DIR / "static" / "imagenes productos"
USER_IMAGES_FOLDER = BASE_DIR / "static" / "imagenes de los usuarios"
EXTENSIONES_IMAGEN = {"png", "jpg", "jpeg", "jfif", "gif", "webp"}
EMPRESA_NOMBRE = "Lycaon"
ROLES_VALIDOS = {"Administrador", "Trabajador", "Cliente"}

DB_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
DB_USER = os.getenv("MYSQL_USER", "root")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
DB_NAME = os.getenv("MYSQL_DATABASE", "rock corporation")
DB_PORT = int(os.getenv("MYSQL_PORT", "3306"))
CREATE_TABLE_USUARIOS = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_completo VARCHAR(120) NOT NULL,
    correo VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('Administrador', 'Trabajador', 'Cliente') NOT NULL,
    foto_perfil VARCHAR(500) NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado ENUM('activo', 'inactivo') NOT NULL DEFAULT 'activo'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_TABLE_PRODUCTOS = """
CREATE TABLE IF NOT EXISTS productos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    descripcion TEXT NULL,
    imagen_url VARCHAR(500) NULL,
    precio DECIMAL(10, 2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_TABLE_CARRITO = """
CREATE TABLE IF NOT EXISTS carrito (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NULL,
    session_key VARCHAR(120) NULL,
    producto_id INT NOT NULL,
    cantidad INT NOT NULL DEFAULT 1,
    fecha_agregado TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizado TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_usuario_producto (usuario_id, producto_id),
    UNIQUE KEY unique_session_producto (session_key, producto_id),
    CONSTRAINT fk_carrito_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_carrito_producto FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_TABLE_MIGRACIONES = """
CREATE TABLE IF NOT EXISTS migraciones (
    nombre VARCHAR(80) PRIMARY KEY,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

PRODUCTOS_INICIALES = [
    (
        "Guitarra Gibson",
        "Guitarra electrica profesional con sonido potente para escenario.",
        "https://images.unsplash.com/photo-1564186763535-ebb21ef5277f?auto=format&fit=crop&w=900&q=80",
        1200,
        5,
    ),
    (
        "Bajo Fender",
        "Bajo clasico para rock, funk y grabacion en estudio.",
        "https://images.unsplash.com/photo-1510915361894-db8b60106cb1?auto=format&fit=crop&w=900&q=80",
        850,
        3,
    ),
]

IMAGENES_INSTRUMENTOS = {
    "Guitarra electrica": "electric,guitar,instrument",
    "Guitarra acustica": "acoustic,guitar,instrument",
    "Guitarra electroacustica": "acoustic,electric,guitar",
    "Bajo electrico": "bass,guitar,instrument",
    "Bajo acustico": "acoustic,bass,guitar",
    "Ukelele": "ukulele,instrument",
    "Mandolina": "mandolin,instrument",
    "Banjo": "banjo,instrument",
    "Violin": "violin,instrument",
    "Viola": "viola,string,instrument",
    "Violonchelo": "cello,instrument",
    "Contrabajo": "double,bass,instrument",
    "Piano digital": "digital,piano,keyboard",
    "Teclado arranger": "music,keyboard,instrument",
    "Sintetizador": "synthesizer,keyboard,instrument",
    "Controlador MIDI": "midi,controller,keyboard",
    "Acordeon": "accordion,instrument",
    "Melodica": "melodica,instrument",
    "Bateria acustica": "drum,set,instrument",
    "Bateria electronica": "electronic,drums,instrument",
    "Caja redoblante": "snare,drum,instrument",
    "Bombo de marcha": "bass,drum,instrument",
    "Congas": "conga,drums,instrument",
    "Bongos": "bongo,drums,instrument",
    "Timbal latino": "timbales,drums,instrument",
    "Cajon peruano": "cajon,drum,instrument",
    "Djembe": "djembe,drum,instrument",
    "Tambor alegre": "hand,drum,instrument",
    "Maracas": "maracas,instrument",
    "Pandereta": "tambourine,instrument",
    "Triangulo": "triangle,percussion,instrument",
    "Xilofono": "xylophone,instrument",
    "Marimba": "marimba,instrument",
    "Vibrafono": "vibraphone,instrument",
    "Flauta traversa": "flute,instrument",
    "Flauta dulce": "recorder,flute,instrument",
    "Clarinete": "clarinet,instrument",
    "Saxofon alto": "alto,saxophone,instrument",
    "Saxofon tenor": "tenor,saxophone,instrument",
    "Oboe": "oboe,instrument",
    "Fagot": "bassoon,instrument",
    "Trompeta": "trumpet,instrument",
    "Trombon": "trombone,instrument",
    "Corno frances": "french,horn,instrument",
    "Tuba": "tuba,instrument",
    "Eufonio": "euphonium,instrument",
    "Arpa": "harp,instrument",
    "Cuatro llanero": "cuatro,guitar,instrument",
    "Tiple": "tiple,guitar,instrument",
    "Charango": "charango,instrument",
}

ADMIN_INICIAL_CORREO = os.getenv("ADMIN_EMAIL", "admin@rock.com")
ADMIN_INICIAL_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin12345")


CREATE_TABLE_PEDIDOS = """
CREATE TABLE IF NOT EXISTS pedidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NULL,
    nombre_cliente VARCHAR(120) NOT NULL,
    correo_cliente VARCHAR(150) NOT NULL,
    direccion VARCHAR(255) NOT NULL,
    ciudad VARCHAR(100) NOT NULL,
    codigo_postal VARCHAR(20) NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    metodo_pago VARCHAR(50) NOT NULL,
    estado ENUM('Pendiente', 'Pagado', 'Enviado', 'Cancelado') NOT NULL DEFAULT 'Pagado',
    fecha_pedido TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pedidos_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_TABLE_PEDIDO_DETALLES = """
CREATE TABLE IF NOT EXISTS pedido_detalles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id INT NOT NULL,
    producto_id INT NOT NULL,
    cantidad INT NOT NULL DEFAULT 1,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    CONSTRAINT fk_detalles_pedido FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
    CONSTRAINT fk_detalles_producto FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


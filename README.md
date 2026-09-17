# 🎸 Rock Corporation - E-Commerce de Instrumentos Musicales

Plataforma e-commerce completa y moderna desarrollada en **Python (Flask)** y **MySQL**, especializada en la venta de instrumentos musicales, gestión de inventario, panel administrativo, autenticación de usuarios y reportes PDF.

---

## 🚀 Características Principales

- **Catálogo de Productos:** Exploración por categorías, búsqueda en tiempo real, filtros y vistas detalladas de instrumentos musicales.
- **Carrito de Compras y Checkout:** Gestión de carrito para invitados y usuarios autenticados, proceso de compra con registro de pedidos.
- **Gestión de Usuarios y Roles:** Autenticación fluida (Login, Registro, Recuperación de contraseña, Perfil) con roles de **Cliente** y **Administrador**.
- **Panel Administrativo (Dashboard):** Métricas en tiempo real, gestión completa de productos (CRUD), gestión de usuarios y pedidos.
- **Generación de Reportes PDF:** Descarga de reportes oficiales de productos y usuarios utilizando ReportLab.
- **Diseño Moderno y Responsivo:** Interfaz oscura (dark theme) con estilos rock/metal, animaciones suaves y microinteracciones.

---

## 🛠️ Tecnologías Utilizadas

- **Backend:** Python 3.x, Flask, PyMySQL, ReportLab, Werkzeug
- **Frontend:** HTML5 Semántico, CSS3 personalizado, JavaScript moderno, Bootstrap 5, FontAwesome
- **Base de Datos:** MySQL (compatible con XAMPP / WampServer / MariaDB)

---

## 📂 Estructura del Proyecto

`	ext
ROCK CORPORATION v1/
├── app.py                     # Punto de entrada del servidor Flask
├── .env.example               # Plantilla de variables de entorno
├── models/                    # Lógica de datos, controladores y base de datos
│   ├── app_instance.py        # Instancia central de la app Flask
│   ├── config.py              # Configuración y constantes del sistema
│   ├── database.py            # Conexión y creación de esquemas MySQL
│   ├── models.py              # Operaciones de negocio y consultas
│   └── controllers.py         # Controladores y rutas de la aplicación
├── utils/                     # Módulos y servicios auxiliares
│   ├── __init__.py
│   └── pdf_generator.py       # Generación de reportes PDF descargables
├── scripts/                   # Scripts de mantenimiento y base de datos
│   ├── setup_xampp.py         # Inicializador y comprobador de XAMPP / MySQL
│   ├── update_images.py       # Script de actualización de imágenes
│   └── rock_corporation_xampp.sql # Esquema SQL de respaldo
├── static/                    # Archivos estáticos (CSS, JS, imágenes, fuentes)
└── templates/                 # Plantillas HTML divididas por módulo
    ├── admin/                 # Panel de administración
    ├── auth/                  # Autenticación (Login, Registro, etc.)
    ├── shop/                  # Tienda y compras
    ├── user/                  # Perfil de usuario y pedidos
    └── base.html              # Plantilla base
`

---

## ⚙️ Instalación y Puesta en Marcha

### 1. Clonar el repositorio
`ash
git clone https://github.com/TU-USUARIO/rock-corporation.git
cd rock-corporation
`

### 2. Crear y activar entorno virtual
`ash
python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En Linux / Mac:
source .venv/bin/activate
`

### 3. Instalar dependencias
`ash
pip install flask pymysql reportlab werkzeug
`

### 4. Configurar Base de Datos (XAMPP / MySQL)
Asegúrate de tener iniciado el servicio **MySQL** en XAMPP y ejecuta:
`ash
python scripts/setup_xampp.py
`

### 5. Iniciar la aplicación
`ash
python app.py
`
Abre tu navegador en http://127.0.0.1:5000.

---

## 👤 Credenciales por Defecto

- **Usuario Admin:** dmin@rock.com
- **Contraseña Admin:** Admin12345

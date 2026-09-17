-- ============================================================================
-- BASE DE DATOS ROCK CORPORATION PARA XAMPP / PHPMYADMIN / MYSQL
-- ============================================================================
-- Instrucciones para XAMPP:
-- 1. Abre XAMPP Control Panel e inicia Apache y MySQL.
-- 2. Ve a http://localhost/phpmyadmin/ en tu navegador.
-- 3. Haz clic en "Importar", selecciona este archivo y presiona "Continuar".
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `rock corporation` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `rock corporation`;

-- ----------------------------------------------------------------------------
-- Tabla: usuarios
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `usuarios` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre_completo` VARCHAR(255) NOT NULL,
  `correo` VARCHAR(255) NOT NULL UNIQUE,
  `password_hash` VARCHAR(255) NOT NULL,
  `rol` VARCHAR(50) NOT NULL DEFAULT 'Cliente',
  `estado` VARCHAR(50) NOT NULL DEFAULT 'activo',
  `foto_perfil` VARCHAR(500) DEFAULT NULL,
  `direccion_casa` VARCHAR(255) DEFAULT NULL,
  `ciudad` VARCHAR(100) DEFAULT NULL,
  `codigo_postal` VARCHAR(50) DEFAULT NULL,
  `tarjeta_enmascarada` VARCHAR(100) DEFAULT NULL,
  `metodo_pago_guardado` VARCHAR(100) DEFAULT NULL,
  `codigo_verificacion` VARCHAR(10) DEFAULT NULL,
  `email_verificado` TINYINT(1) DEFAULT 0,
  `fecha_registro` DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_usuarios_correo` (`correo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- Tabla: productos
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `productos` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(255) NOT NULL,
  `descripcion` TEXT,
  `imagen_url` VARCHAR(500),
  `precio` DECIMAL(12, 2) NOT NULL,
  `stock` INT NOT NULL DEFAULT 0,
  INDEX `idx_productos_nombre_precio` (`nombre`, `precio`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- Tabla: carrito
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `carrito` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `usuario_id` INT DEFAULT NULL,
  `session_key` VARCHAR(255) DEFAULT NULL,
  `producto_id` INT NOT NULL,
  `cantidad` INT NOT NULL DEFAULT 1,
  FOREIGN KEY (`producto_id`) REFERENCES `productos`(`id`) ON DELETE CASCADE,
  INDEX `idx_carrito_usuario_session` (`usuario_id`, `session_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- Tabla: pedidos
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `pedidos` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `usuario_id` INT DEFAULT NULL,
  `nombre_cliente` VARCHAR(255) NOT NULL,
  `correo_cliente` VARCHAR(255) NOT NULL,
  `direccion` VARCHAR(255) NOT NULL,
  `ciudad` VARCHAR(255) NOT NULL,
  `codigo_postal` VARCHAR(50) NOT NULL,
  `metodo_pago` VARCHAR(100) NOT NULL,
  `total` DECIMAL(12, 2) NOT NULL,
  `estado` VARCHAR(50) NOT NULL DEFAULT 'Pagado',
  `fecha_creacion` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- Tabla: pedido_detalles
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `pedido_detalles` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `pedido_id` INT NOT NULL,
  `producto_id` INT DEFAULT NULL,
  `nombre_producto` VARCHAR(255) NOT NULL,
  `precio_unitario` DECIMAL(12, 2) NOT NULL,
  `cantidad` INT NOT NULL,
  `subtotal` DECIMAL(12, 2) NOT NULL,
  FOREIGN KEY (`pedido_id`) REFERENCES `pedidos`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- Tabla: migraciones
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `migraciones` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(255) NOT NULL UNIQUE,
  `fecha` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- Datos Iniciales: Usuario Administrador (Password: Admin12345)
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO `usuarios` (`id`, `nombre_completo`, `correo`, `password_hash`, `rol`, `estado`, `email_verificado`) VALUES
(1, 'Administrador Rock', 'admin@rock.com', 'scrypt:32768:8:1$7f6N8jQZ$5a3a40b8a1c9e8020942d99d1fa980998f8285514fcfb297b48981f9a15061ff', 'Administrador', 'activo', 1);

-- ----------------------------------------------------------------------------
-- Datos Iniciales: 10 Productos Emblemáticos (Precios en COP)
-- ----------------------------------------------------------------------------
TRUNCATE TABLE `productos`;
INSERT INTO `productos` (`id`, `nombre`, `descripcion`, `imagen_url`, `precio`, `stock`) VALUES
(1, 'Guitarra Eléctrica Pro', 'Guitarra eléctrica profesional con cuerpo de caoba y pastillas de alta ganancia.', '/static/imagenes productos/premium_guitar.jpg', 5000000.00, 8),
(2, 'Guitarra Acústica Classic', 'Guitarra acústica de madera seleccionada con sonido cálido y resonancia profunda.', '/static/imagenes productos/premium_guitar.jpg', 1800000.00, 12),
(3, 'Bajo Eléctrico Studio', 'Bajo eléctrico de 4 cuerdas ideal para rock, funk y grabación profesional en estudio.', '/static/imagenes productos/premium_bass.jpg', 3560000.00, 6),
(4, 'Piano Digital Deluxe', 'Piano digital de 88 teclas pesadas con respuesta al tacto y múltiples voces de piano.', '/static/imagenes productos/premium_piano.jpg', 5800000.00, 5),
(5, 'Batería Acústica Stage', 'Set completo de batería acústica con platillos de bronce y herrajes reinforced.', '/static/imagenes productos/premium_drums.jpg', 7400000.00, 4),
(6, 'Saxofón Alto Gold', 'Saxofón alto en Mi bemol con acabado dorado y sonido brillante para jazz y bandas.', '/static/imagenes productos/premium_woodwind.jpg', 4400000.00, 7),
(7, 'Trompeta de Concierto', 'Trompeta en Si bemol de latón dorado con afinación precisa y estuche rígido.', '/static/imagenes productos/premium_brass.jpg', 2480000.00, 9),
(8, 'Violín de Concierto', 'Violín 4/4 tallado a mano con arco de madera de brasil y estuche acolchado.', '/static/imagenes productos/premium_violin.jpg', 3120000.00, 6),
(9, 'Set de Congas Latinas', 'Pareja de congas de madera de roble con parches de cuero natural y soporte metálico.', '/static/imagenes productos/premium_percussion.jpg', 2720000.00, 10),
(10, 'Ukelele Soprano', 'Ukelele soprano tradicional en madera de acacia con cuerdas Aquila de alta calidad.', '/static/imagenes productos/premium_ukulele.jpg', 480000.00, 15);

-- ----------------------------------------------------------------------------
-- Registro de Migración
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO `migraciones` (`nombre`) VALUES ('migracion_pesos_colombianos_cop_v2');

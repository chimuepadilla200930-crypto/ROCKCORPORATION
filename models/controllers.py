import re
from functools import wraps
from uuid import uuid4

from flask import flash, redirect, render_template, request, session, url_for, Response
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from .app_instance import app
from .config import *
from .models import *
from utils.pdf_generator import (
    generar_pdf_reporte_productos,
    generar_pdf_reporte_producto_individual,
    generar_pdf_reporte_usuarios
)

def verificar_password(almacenada, ingresada):
    if not almacenada or not ingresada:
        return False
    if almacenada == ingresada:
        return True
    # Compatibilidad en caso de que existan hashes previos en la base de datos
    if str(almacenada).startswith(("scrypt:", "pbkdf2:", "argon2:")):
        try:
            return check_password_hash(almacenada, ingresada)
        except Exception:
            return False
    return False

TASA_COP_USD = 3500.0

@app.template_filter("formato_cop")
def filtro_formato_cop(val):
    try:
        precio_val = float(val or 0)
        return f"${precio_val:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "$0"

@app.template_filter("estimacion_usd")
def filtro_estimacion_usd(val):
    try:
        precio_val = float(val or 0)
        usd_val = precio_val / TASA_COP_USD
        return f"${usd_val:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"

# ============================================================================
# UTILIDADES DE CONTROLADOR
# ============================================================================

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if not session.get("usuario_id"):
                flash("Inicia sesión para continuar.", "error")
                return redirect(url_for("login"))

            if session.get("usuario_rol") not in roles:
                flash("No tienes permisos para acceder a esta sección.", "error")
                return redirect(url_for("index"))

            return view(*args, **kwargs)

        return wrapped_view

    return decorator


admin_required = role_required("Administrador")

def obtener_usuario_actual():
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return None

    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre_completo, correo, rol, estado, fecha_registro, foto_perfil,
                       direccion_casa, ciudad, codigo_postal, tarjeta_enmascarada, metodo_pago_guardado
                FROM usuarios
                WHERE id = %s
                """,
                (usuario_id,),
            )
            return cursor.fetchone()


def guardar_imagen_producto(archivo):
    if not archivo or not archivo.filename:
        return None

    extension = archivo.filename.rsplit(".", 1)[-1].lower()
    if "." not in archivo.filename or extension not in EXTENSIONES_IMAGEN:
        raise ValueError("La imagen debe ser PNG, JPG, JPEG, JFIF, GIF o WEBP.")

    PRODUCT_IMAGES_FOLDER.mkdir(parents=True, exist_ok=True)
    nombre_base = secure_filename(archivo.filename.rsplit(".", 1)[0]) or "producto"
    nombre_archivo = f"{nombre_base}-{uuid4().hex[:10]}.{extension}"
    archivo.save(PRODUCT_IMAGES_FOLDER / nombre_archivo)
    return url_for("static", filename=f"imagenes productos/{nombre_archivo}")


def guardar_foto_perfil(archivo):
    if not archivo or not archivo.filename:
        return None

    extension = archivo.filename.rsplit(".", 1)[-1].lower()
    if "." not in archivo.filename or extension not in EXTENSIONES_IMAGEN:
        raise ValueError("La foto debe ser PNG, JPG, JPEG, JFIF, GIF o WEBP.")

    USER_IMAGES_FOLDER.mkdir(parents=True, exist_ok=True)
    nombre_base = secure_filename(archivo.filename.rsplit(".", 1)[0]) or "perfil"
    nombre_archivo = f"perfil-{nombre_base}-{uuid4().hex[:10]}.{extension}"
    archivo.save(USER_IMAGES_FOLDER / nombre_archivo)
    return url_for("static", filename=f"imagenes de los usuarios/{nombre_archivo}")


def correo_valido(correo):
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo) is not None


def obtener_apellidos_usuario(nombre_completo):
    partes_nombre = nombre_completo.split()
    if len(partes_nombre) >= 2:
        return " ".join(partes_nombre[-2:])
    return nombre_completo


# ============================================================================
# VISTA - CONTEXTO COMPARTIDO
# ============================================================================

def datos_usuario_menu():
    nombre_usuario = session.get("usuario_nombre", "")
    return {
        "usuario_nombre_menu": obtener_apellidos_usuario(nombre_usuario),
        "usuario_foto_menu": session.get("usuario_foto"),
        "total_carrito": obtener_total_carrito(),
    }


# ============================================================================
# CONTROLADORES - PUBLICO Y AUTENTICACION
# ============================================================================

@app.route("/")
def index():
    return render_template("shop/index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = (request.form.get("username", "") or request.form.get("email", "")).strip().lower()
        password = request.form.get("password", "")

        if not correo or not password:
            flash("Por favor ingresa tu correo y contraseña.", "error")
            return redirect(url_for("login"))

        init_db()
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, nombre_completo, correo, password_hash, rol, estado, foto_perfil
                    FROM usuarios
                    WHERE correo = %s
                    """,
                    (correo,),
                )
                usuario = cursor.fetchone()

        if not usuario or not verificar_password(usuario["password_hash"], password):
            flash("El correo o la contraseña no son correctos.", "error")
            return redirect(url_for("login"))

        if usuario["estado"] != "activo":
            flash("Tu cuenta no está activa. Escríbenos a soporte si necesitas ayuda.", "error")
            return redirect(url_for("login"))

        session["usuario_id"] = usuario["id"]
        session["usuario_nombre"] = usuario["nombre_completo"]
        session["usuario_rol"] = usuario["rol"]
        session["usuario_foto"] = usuario["foto_perfil"]
        fusionar_carrito_invitado(usuario["id"])

        primer_nombre = usuario["nombre_completo"].split()[0]
        flash(f"¡Qué bueno tenerte de vuelta, {primer_nombre}!", "success")
        return redirect(url_for("index"))

    return render_template("auth/login_user.html")


@app.route("/recuperar-password", methods=["GET", "POST"])
def recuperar_password():
    correo_inicial = request.args.get("correo", "").strip().lower()

    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        nueva_password = request.form.get("nueva_password", "")
        confirmar_password = request.form.get("confirmar_password", "")

        if not all([correo, nueva_password, confirmar_password]):
            flash("Por favor completa todos los campos.", "error")
            return redirect(url_for("recuperar_password", correo=correo))

        if not correo_valido(correo):
            flash("Ingresa un correo electrónico válido.", "error")
            return redirect(url_for("recuperar_password", correo=correo))

        if len(nueva_password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.", "error")
            return redirect(url_for("recuperar_password", correo=correo))

        if nueva_password != confirmar_password:
            flash("Las contraseñas no coinciden. Inténtalo de nuevo.", "error")
            return redirect(url_for("recuperar_password", correo=correo))

        init_db()
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM usuarios WHERE correo = %s", (correo,))
                usuario = cursor.fetchone()

                if not usuario:
                    flash("No encontramos ninguna cuenta con ese correo.", "error")
                    return redirect(url_for("recuperar_password", correo=correo))

                cursor.execute(
                    "UPDATE usuarios SET password_hash = %s WHERE id = %s",
                    (nueva_password, usuario["id"]),
                )

        flash("Contraseña actualizada con éxito. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("login"))

    return render_template("auth/recuperar_password.html", correo=correo_inicial)


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([nombre, correo, password, confirm_password]):
            flash("Por favor completa todos los datos solicitados.", "error")
            return redirect(url_for("registro"))

        if not correo_valido(correo):
            flash("Ingresa un correo electrónico válido.", "error")
            return redirect(url_for("registro"))

        if len(password) < 8:
            flash("La contraseña debe tener mínimo 8 caracteres.", "error")
            return redirect(url_for("registro"))

        if password != confirm_password:
            flash("Las contraseñas no coinciden.", "error")
            return redirect(url_for("registro"))

        init_db()
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM usuarios WHERE correo = %s", (correo,))
                if cursor.fetchone():
                    flash("Ese correo ya está registrado. Prueba iniciando sesión.", "error")
                    return redirect(url_for("registro"))

                cursor.execute(
                    """
                    INSERT INTO usuarios (nombre_completo, correo, password_hash, rol, estado)
                    VALUES (%s, %s, %s, 'Cliente', 'activo')
                    """,
                    (nombre, correo, password),
                )
                nuevo_usuario_id = cursor.lastrowid

        session["usuario_id"] = nuevo_usuario_id
        session["usuario_nombre"] = nombre
        session["usuario_rol"] = "Cliente"
        session["usuario_foto"] = None
        fusionar_carrito_invitado(nuevo_usuario_id)

        primer_nombre = nombre.split()[0]
        flash(f"¡Bienvenido a Rock Corporation, {primer_nombre}! Tu cuenta está lista.", "success")
        return redirect(url_for("index"))

    return render_template("auth/registro.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión. ¡Esperamos verte pronto!", "success")
    return redirect(url_for("index"))


# ============================================================================
# CONTROLADORES - TIENDA Y CARRITO
# ============================================================================

@app.route("/tienda")
def client_shop():
    categoria = request.args.get("categoria", "").strip()
    busqueda = request.args.get("buscar", "").strip()
    productos = filtrar_productos_tienda(obtener_productos(), categoria, busqueda)
    categorias_tienda = obtener_categorias_tienda()
    categoria_activa = next(
        (item for item in categorias_tienda if item["slug"] == categoria),
        None,
    )
    return render_template(
        "shop/client_shop.html",
        productos=productos,
        categorias=categorias_tienda,
        categoria_activa=categoria_activa,
        categoria_slug=categoria,
        busqueda=busqueda,
    )


@app.route("/carrito/agregar/<int:producto_id>", methods=["POST"])
def agregar_carrito(producto_id):
    producto = agregar_producto_carrito(producto_id)
    if not producto:
        flash("El producto no existe.", "error")
        return redirect(url_for("client_shop"))

    if producto.get("sin_stock"):
        flash(f"{producto['nombre']} no tiene stock disponible.", "error")
    elif producto.get("limite_stock"):
        flash(f"{producto['nombre']} ya alcanzo el stock disponible.", "error")
    elif producto.get("cantidad", 1) > 1:
        flash(f"Se sumo otra unidad de {producto['nombre']} al carrito.", "success")
    else:
        flash(f"{producto['nombre']} anadido al carrito.", "success")

    session["ultimo_producto_carrito"] = producto_id
    return redirect(url_for("client_shop"))


@app.route("/comprar-ahora/<int:producto_id>", methods=["POST"])
def comprar_ahora(producto_id):
    producto = agregar_producto_carrito(producto_id)
    if not producto:
        flash("El producto no existe.", "error")
        return redirect(url_for("client_shop"))

    if producto.get("sin_stock"):
        flash(f"{producto['nombre']} no tiene stock disponible.", "error")
        return redirect(url_for("client_shop"))

    if producto.get("limite_stock"):
        flash(f"{producto['nombre']} ya alcanzo el stock disponible.", "error")
    else:
        flash(f"{producto['nombre']} esta listo para comprar.", "success")

    session["ultimo_producto_carrito"] = producto_id
    return redirect(url_for("ver_carrito"))


@app.route("/carrito")
def ver_carrito():
    items, total = obtener_items_carrito()
    return render_template("shop/carrito.html", items=items, total=total)


@app.route("/carrito/actualizar/<int:item_id>", methods=["POST"])
def actualizar_carrito(item_id):
    try:
        cantidad = int(request.form.get("cantidad", "1"))
    except ValueError:
        cantidad = 1

    exito, mensaje = actualizar_item_carrito(item_id, cantidad)
    flash(mensaje, "success" if exito else "error")
    return redirect(url_for("ver_carrito"))


@app.route("/carrito/eliminar/<int:item_id>", methods=["POST"])
def eliminar_carrito(item_id):
    if eliminar_item_carrito(item_id):
        flash("Producto eliminado del carrito.", "success")
    else:
        flash("No se pudo eliminar el producto.", "error")
    return redirect(url_for("ver_carrito"))


@app.route("/carrito/vaciar", methods=["POST"])
def vaciar_carrito():
    vaciar_carrito_actual()
    flash("Carrito vaciado correctamente.", "success")
    return redirect(url_for("ver_carrito"))


@app.route("/carrito/finalizar", methods=["POST"])
def finalizar_carrito():
    exito, mensaje = finalizar_compra_actual()
    flash(mensaje, "success" if exito else "error")
    return redirect(url_for("ver_carrito"))


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total = obtener_items_carrito()
    if not items:
        flash("Tu carrito esta vacio.", "error")
        return redirect(url_for("client_shop"))

    usuario = obtener_usuario_actual()
    nombre_defecto = usuario["nombre_completo"] if usuario else ""
    correo_defecto = usuario["correo"] if usuario else ""
    direccion_defecto = usuario.get("direccion_casa", "") if usuario else ""
    ciudad_defecto = usuario.get("ciudad", "") if usuario else ""
    codigo_postal_defecto = usuario.get("codigo_postal", "") if usuario else ""
    metodo_defecto = usuario.get("metodo_pago_guardado", "") if usuario else ""

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        direccion = request.form.get("direccion", "").strip()
        ciudad = request.form.get("ciudad", "").strip()
        codigo_postal = request.form.get("codigo_postal", "").strip()
        metodo_pago = request.form.get("metodo_pago", "Tarjeta de Crédito").strip()

        if not all([nombre, correo, direccion, ciudad, codigo_postal]):
            flash("Por favor, completa todos los campos de envío.", "error")
            return redirect(url_for("checkout"))

        if not correo_valido(correo):
            flash("Ingresa un correo electrónico válido.", "error")
            return redirect(url_for("checkout"))

        usuario_id = session.get("usuario_id")
        pedido_id, mensaje = PedidoModelo.crear(
            usuario_id=usuario_id,
            nombre_cliente=nombre,
            correo_cliente=correo,
            direccion=direccion,
            ciudad=ciudad,
            codigo_postal=codigo_postal,
            metodo_pago=metodo_pago
        )

        if not pedido_id:
            flash(mensaje, "error")
            return redirect(url_for("ver_carrito"))

        # Guardar automáticamente la dirección y tarjeta en la información personal del perfil del usuario
        if usuario_id:
            ultimos_4 = codigo_postal[-4:] if len(codigo_postal) >= 4 else "4242"
            tarjeta_enmascarada = f"•••• •••• •••• {ultimos_4}"
            init_db()
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE usuarios
                        SET direccion_casa = %s,
                            ciudad = %s,
                            codigo_postal = %s,
                            metodo_pago_guardado = %s,
                            tarjeta_enmascarada = %s
                        WHERE id = %s
                        """,
                        (direccion, ciudad, codigo_postal, metodo_pago, tarjeta_enmascarada, usuario_id)
                    )

        flash("¡Pago procesado! Tu información de envío quedó guardada en tu perfil.", "success")
        return redirect(url_for("order_success", order_id=pedido_id))

    return render_template(
        "shop/checkout.html",
        items=items,
        total=total,
        nombre_defecto=nombre_defecto,
        correo_defecto=correo_defecto,
        direccion_defecto=direccion_defecto,
        ciudad_defecto=ciudad_defecto,
        codigo_postal_defecto=codigo_postal_defecto,
        metodo_defecto=metodo_defecto
    )


@app.route("/order-success/<int:order_id>")
def order_success(order_id):
    pedido = PedidoModelo.obtener_por_id(order_id)
    if not pedido:
        flash("El pedido no existe.", "error")
        return redirect(url_for("index"))

    detalles = PedidoModelo.obtener_detalles(order_id)
    return render_template("shop/order_success.html", pedido=pedido, detalles=detalles)


@app.route("/order-receipt/<int:order_id>")
def order_receipt(order_id):
    pedido = PedidoModelo.obtener_por_id(order_id)
    if not pedido:
        flash("El pedido no existe.", "error")
        return redirect(url_for("index"))

    detalles = PedidoModelo.obtener_detalles(order_id)
    return render_template("shop/recibo.html", pedido=pedido, detalles=detalles)


@app.route("/mis-pedidos")
def mis_pedidos():
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        flash("Inicia sesión para ver tu historial de compras.", "error")
        return redirect(url_for("login"))

    pedidos = PedidoModelo.obtener_por_usuario(usuario_id)
    return render_template("user/mis_pedidos.html", pedidos=pedidos)


@app.route("/admin/pedidos")
@admin_required
def admin_pedidos():
    pedidos = PedidoModelo.obtener_todos()
    return render_template("admin/admin_pedidos.html", pedidos=pedidos)


@app.route("/admin/pedido/estado/<int:pedido_id>", methods=["POST"])
@admin_required
def cambiar_estado_pedido(pedido_id):
    nuevo_estado = request.form.get("estado", "").strip()
    estados_validos = {"Pagado", "Enviado", "Entregado", "Cancelado"}

    if nuevo_estado in estados_validos:
        PedidoModelo.actualizar_estado(pedido_id, nuevo_estado)
        flash(f"Estado del pedido #{pedido_id} actualizado a '{nuevo_estado}'.", "success")
    else:
        flash("Estado inválido.", "error")

    return redirect(url_for("admin_pedidos"))


@app.route("/categorias")
def categorias():
    return render_template("shop/categorias.html", categorias=obtener_categorias_tienda())


@app.route("/producto/<int:producto_id>")
def detalle_producto(producto_id):
    producto = obtener_producto_por_id(producto_id)
    if not producto:
        flash("El producto no existe.", "error")
        return redirect(url_for("client_shop"))
    
    # Productos recomendados (mismos de la categoría o aleatorios)
    productos = obtener_productos()
    relacionados = [p for p in productos if p['id'] != producto_id][:4]
    
    return render_template("shop/detalle_producto.html", producto=producto, relacionados=relacionados)


@app.route("/acerca")
def acerca():
    return render_template("user/acerca.html")


@app.route("/contacto")
def contacto():
    return render_template("user/contacto.html")


@app.route("/terminos")
def terminos():
    return render_template("user/terminos.html")
# ============================================================================
# CONTROLADORES - PERFIL
# ============================================================================

@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    usuario = obtener_usuario_actual()
    if not usuario:
        flash("Inicia sesión para ver tu perfil.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        accion = request.form.get("accion", "foto")

        if accion == "password":
            password_actual = request.form.get("password_actual", "")
            nueva_password = request.form.get("nueva_password", "")
            confirmar_password = request.form.get("confirmar_password", "")

            if not all([password_actual, nueva_password, confirmar_password]):
                flash("Completa todos los campos de contraseña.", "error")
                return redirect(url_for("perfil"))

            if len(nueva_password) < 8:
                flash("La nueva contraseña debe tener mínimo 8 caracteres.", "error")
                return redirect(url_for("perfil"))

            if nueva_password != confirmar_password:
                flash("Las contraseñas nuevas no coinciden.", "error")
                return redirect(url_for("perfil"))

            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT password_hash FROM usuarios WHERE id = %s",
                        (usuario["id"],),
                    )
                    usuario_password = cursor.fetchone()

                    if not usuario_password or not verificar_password(usuario_password["password_hash"], password_actual):
                        flash("La contraseña actual no es correcta.", "error")
                        return redirect(url_for("perfil"))

                    cursor.execute(
                        "UPDATE usuarios SET password_hash = %s WHERE id = %s",
                        (nueva_password, usuario["id"]),
                    )

            flash("Contrasena actualizada correctamente.", "success")
            return redirect(url_for("perfil"))

        foto = request.files.get("foto_perfil")
        if not foto or not foto.filename:
            flash("Selecciona una imagen para cambiar tu foto.", "error")
            return redirect(url_for("perfil"))

        try:
            foto_guardada = guardar_foto_perfil(foto)
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("perfil"))

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE usuarios SET foto_perfil = %s WHERE id = %s",
                    (foto_guardada, usuario["id"]),
                )

        session["usuario_foto"] = foto_guardada
        flash("Foto de perfil actualizada.", "success")
        return redirect(url_for("perfil"))

    return render_template("user/perfil.html", usuario=usuario)


@app.route("/perfil/datos-envio", methods=["POST"])
def actualizar_datos_envio_perfil():
    usuario = obtener_usuario_actual()
    if not usuario:
        flash("Inicia sesión para continuar.", "error")
        return redirect(url_for("login"))

    direccion = request.form.get("direccion_casa", "").strip()
    ciudad = request.form.get("ciudad", "").strip()
    codigo_postal = request.form.get("codigo_postal", "").strip()
    numero_tarjeta = request.form.get("numero_tarjeta", "").strip()

    if not all([direccion, ciudad, codigo_postal]):
        flash("Por favor completa los campos de dirección, ciudad y código postal.", "error")
        return redirect(url_for("perfil"))

    tarjeta_enmascarada = usuario.get("tarjeta_enmascarada") or ""
    metodo_pago = usuario.get("metodo_pago_guardado") or "Tarjeta de Crédito"
    if numero_tarjeta:
        ultimos_4 = numero_tarjeta[-4:] if len(numero_tarjeta) >= 4 else (codigo_postal[-4:] if len(codigo_postal) >= 4 else "4242")
        tarjeta_enmascarada = f"•••• •••• •••• {ultimos_4}"
        metodo_pago = f"Tarjeta de Crédito ({tarjeta_enmascarada})"

    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE usuarios
                SET direccion_casa = %s,
                    ciudad = %s,
                    codigo_postal = %s,
                    metodo_pago_guardado = %s,
                    tarjeta_enmascarada = %s
                WHERE id = %s
                """,
                (direccion, ciudad, codigo_postal, metodo_pago, tarjeta_enmascarada, usuario["id"]),
            )

    flash("Información de entrega y método de pago actualizada con éxito.", "success")
    return redirect(url_for("perfil"))


# ============================================================================
# CONTROLADORES - ADMINISTRACION
# ============================================================================

@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin/admin_dashboard.html")


@app.route("/admin/dashboard-data")
@admin_required
def admin_dashboard_data():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS ventas_hoy FROM pedidos WHERE DATE(fecha_pedido) = CURDATE() AND estado = 'Pagado'"
            )
            ventas_hoy = cursor.fetchone().get("ventas_hoy", 0) or 0

            cursor.execute(
                "SELECT COUNT(*) AS proximos_eventos FROM productos WHERE stock < 6"
            )
            proximos_eventos = cursor.fetchone().get("proximos_eventos", 0) or 0

            cursor.execute(
                "SELECT COALESCE(SUM(total), 0) AS ingresos_mes FROM pedidos "
                "WHERE MONTH(fecha_pedido) = MONTH(CURDATE()) "
                "AND YEAR(fecha_pedido) = YEAR(CURDATE()) AND estado = 'Pagado'"
            )
            ingresos_mes = cursor.fetchone().get("ingresos_mes", 0) or 0

            cursor.execute(
                "SELECT nombre_cliente AS usuario, "
                "CONCAT('Realizó una compra de $', total) AS accion, "
                "CASE "
                "WHEN TIMESTAMPDIFF(MINUTE, fecha_pedido, NOW()) < 60 "
                "THEN CONCAT('Hace ', TIMESTAMPDIFF(MINUTE, fecha_pedido, NOW()), ' min') "
                "WHEN TIMESTAMPDIFF(HOUR, fecha_pedido, NOW()) < 24 "
                "THEN CONCAT('Hace ', TIMESTAMPDIFF(HOUR, fecha_pedido, NOW()), ' hr') "
                "ELSE CONCAT('Hace ', TIMESTAMPDIFF(DAY, fecha_pedido, NOW()), ' d') "
                "END AS fecha "
                "FROM pedidos "
                "ORDER BY fecha_pedido DESC "
                "LIMIT 5"
            )
            actividad = cursor.fetchall()

    return {
        "ventas_hoy": int(ventas_hoy),
        "proximos_eventos": int(proximos_eventos),
        "ingresos_mes": float(ingresos_mes),
        "actividad": actividad,
    }



@app.route("/admin/productos", methods=["GET", "POST"])
@admin_required
def admin_productos():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        imagen_url = request.form.get("imagen_url", "").strip()
        imagen_archivo = request.files.get("imagen_archivo")
        precio = request.form.get("precio", "").strip()
        stock = request.form.get("stock", "").strip()

        if not nombre or not descripcion or not precio or not stock:
            flash("Completa todos los datos del producto.", "error")
            return redirect(url_for("admin_productos"))

        if not imagen_url and (not imagen_archivo or not imagen_archivo.filename):
            flash("Agrega una imagen por URL o sube una imagen desde tu equipo.", "error")
            return redirect(url_for("admin_productos"))

        try:
            precio_numero = float(precio)
            stock_numero = int(stock)
        except ValueError:
            flash("Precio y stock deben ser numeros validos.", "error")
            return redirect(url_for("admin_productos"))

        if precio_numero < 0 or stock_numero < 0:
            flash("Precio y stock no pueden ser negativos.", "error")
            return redirect(url_for("admin_productos"))

        try:
            imagen_guardada = guardar_imagen_producto(imagen_archivo)
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("admin_productos"))

        imagen_producto = imagen_guardada or imagen_url

        init_db()
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO productos (nombre, descripcion, imagen_url, precio, stock)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (nombre, descripcion, imagen_producto, precio_numero, stock_numero),
                )

        flash("Producto agregado correctamente.", "success")
        return redirect(url_for("admin_productos"))

    return render_template("admin/admin_productos.html", productos=obtener_productos())


@app.route("/admin/producto/eliminar/<int:producto_id>", methods=["POST"])
@admin_required
def eliminar_producto(producto_id):
    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM productos WHERE id = %s", (producto_id,))
    flash("Producto eliminado correctamente.", "success")
    return redirect(url_for("admin_productos"))


@app.route("/admin/producto/actualizar/<int:producto_id>", methods=["GET", "POST"])
@admin_required
def actualizar_producto(producto_id):
    producto = obtener_producto_por_id(producto_id)
    if not producto:
        flash("El producto no existe.", "error")
        return redirect(url_for("admin_productos"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        imagen_url = request.form.get("imagen_url", "").strip()
        imagen_archivo = request.files.get("imagen_archivo")
        precio = request.form.get("precio", "").strip()
        stock = request.form.get("stock", "").strip()

        if not nombre or not descripcion or not precio or not stock:
            flash("Completa todos los datos del producto.", "error")
            return redirect(url_for("actualizar_producto", producto_id=producto_id))

        try:
            precio_numero = float(precio)
            stock_numero = int(stock)
        except ValueError:
            flash("Precio y stock deben ser números válidos.", "error")
            return redirect(url_for("actualizar_producto", producto_id=producto_id))

        if precio_numero < 0 or stock_numero < 0:
            flash("Precio y stock no pueden ser negativos.", "error")
            return redirect(url_for("actualizar_producto", producto_id=producto_id))

        try:
            imagen_guardada = guardar_imagen_producto(imagen_archivo)
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("actualizar_producto", producto_id=producto_id))

        imagen_producto = imagen_guardada or imagen_url or producto["imagen_url"]

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE productos
                    SET nombre = %s,
                        descripcion = %s,
                        imagen_url = %s,
                        precio = %s,
                        stock = %s
                    WHERE id = %s
                    """,
                    (nombre, descripcion, imagen_producto, precio_numero, stock_numero, producto_id),
                )

        flash("Producto actualizado correctamente.", "success")
        return redirect(url_for("admin_productos"))

    return render_template("admin/actualizar_producto.html", producto=producto)


@app.route("/admin/reporte/productos/pdf")
@admin_required
def reporte_productos_pdf():
    productos = obtener_productos()
    pdf_bytes = generar_pdf_reporte_productos(productos, tasa_cop_usd=TASA_COP_USD)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_productos_rock_corp.pdf"}
    )


@app.route("/admin/reporte/producto/<int:producto_id>/pdf")
@admin_required
def reporte_producto_individual_pdf(producto_id):
    producto = obtener_producto_por_id(producto_id)
    if not producto:
        flash("Producto no encontrado.", "error")
        return redirect(url_for("admin_productos"))

    pdf_bytes = generar_pdf_reporte_producto_individual(producto, tasa_cop_usd=TASA_COP_USD)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_producto_{producto_id}.pdf"}
    )


@app.route("/admin/reporte/usuarios/pdf")
@admin_required
def reporte_usuarios_pdf():
    usuarios = obtener_usuarios_admin()
    pdf_bytes = generar_pdf_reporte_usuarios(usuarios)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_usuarios_rock_corp.pdf"}
    )


@app.route("/admin/usuarios")
@admin_required
def admin_usuarios():
    return render_template("admin/admin_usuarios.html", usuarios=obtener_usuarios_admin())

@app.route("/admin/usuario/reportar/<int:usuario_id>", methods=["GET", "POST"])
@admin_required
def reportar_usuario(usuario_id):
    usuario = obtener_usuario_admin_por_id(usuario_id)
    if not usuario:
        flash("El usuario no existe.", "error")
        return redirect(url_for("admin_usuarios"))

    if request.method == "POST":
        motivo = request.form.get("motivo", "").strip()
        duracion = request.form.get("duracion", "").strip()
        explicacion = request.form.get("explicacion", "").strip()

        if not motivo or not duracion:
            flash("Debes seleccionar el motivo y la duración de la suspensión.", "error")
            return render_template("admin/reportar_usuario.html", usuario=usuario)

        init_db()
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE usuarios SET estado = 'inactivo' WHERE id = %s",
                    (usuario_id,),
                )

        flash(f"Usuario '{usuario['nombre']}' ha sido suspendido.", "success")
        return redirect(url_for("admin_usuarios"))

    return render_template("admin/reportar_usuario.html", usuario=usuario)


@app.route("/admin/usuario/actualizar/<int:usuario_id>", methods=["GET", "POST"])
@admin_required
def actualizar_usuario(usuario_id):
    usuario = obtener_usuario_admin_por_id(usuario_id)
    if not usuario:
        flash("El usuario no existe.", "error")
        return redirect(url_for("admin_usuarios"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        rol = request.form.get("rol", "").strip()
        estado = request.form.get("estado", "").strip()
        nueva_password = request.form.get("nueva_password", "")

        if not all([nombre, correo, rol, estado]):
            flash("Completa los datos del usuario.", "error")
            return redirect(url_for("actualizar_usuario", usuario_id=usuario_id))

        if not correo_valido(correo):
            flash("Ingresa un correo electrónico válido.", "error")
            return redirect(url_for("actualizar_usuario", usuario_id=usuario_id))

        if rol not in ROLES_VALIDOS:
            flash("Selecciona un rol válido.", "error")
            return redirect(url_for("actualizar_usuario", usuario_id=usuario_id))

        if estado not in {"activo", "inactivo"}:
            flash("Selecciona un estado válido.", "error")
            return redirect(url_for("actualizar_usuario", usuario_id=usuario_id))

        if nueva_password and len(nueva_password) < 8:
            flash("La contraseña debe tener mínimo 8 caracteres.", "error")
            return redirect(url_for("actualizar_usuario", usuario_id=usuario_id))

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM usuarios WHERE correo = %s AND id <> %s",
                    (correo, usuario_id),
                )
                if cursor.fetchone():
                    flash("El correo ya está registrado por otro usuario.", "error")
                    return redirect(url_for("actualizar_usuario", usuario_id=usuario_id))

                if nueva_password:
                    cursor.execute(
                        """
                        UPDATE usuarios
                        SET nombre_completo = %s,
                            correo = %s,
                            rol = %s,
                            estado = %s,
                            password_hash = %s
                        WHERE id = %s
                        """,
                        (nombre, correo, rol, estado, nueva_password, usuario_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE usuarios
                        SET nombre_completo = %s,
                            correo = %s,
                            rol = %s,
                            estado = %s
                        WHERE id = %s
                        """,
                        (nombre, correo, rol, estado, usuario_id),
                    )

        if session.get("usuario_id") == usuario_id:
            session["usuario_nombre"] = nombre
            session["usuario_rol"] = rol

        flash("Usuario actualizado correctamente.", "success")
        return redirect(url_for("admin_usuarios"))

    return render_template(
        "admin/actualizar_usuario.html",
        usuario=usuario,
        roles=sorted(ROLES_VALIDOS),
    )


@app.route("/admin/usuario/prohibir/<int:usuario_id>", methods=["POST"])
@admin_required
def prohibir_usuario(usuario_id):
    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE usuarios SET estado = 'inactivo' WHERE id = %s",
                (usuario_id,),
            )
    flash("Compras bloqueadas para el usuario.", "success")
    return redirect(url_for("admin_usuarios"))


@app.route("/admin/usuario/eliminar/<int:usuario_id>", methods=["POST"])
@admin_required
def eliminar_usuario(usuario_id):
    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
    flash("Usuario eliminado correctamente.", "success")
    return redirect(url_for("admin_usuarios"))



class ControladorPrincipal:
    """Agrupa las rutas registradas para la aplicacion."""

    @staticmethod
    def registrar_contexto():
        app.context_processor(datos_usuario_menu)

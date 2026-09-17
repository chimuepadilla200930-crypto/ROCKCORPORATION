if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from rock_mvc import app, init_db
    print("Tablas MySQL creadas/verificadas correctamente.")
    print("Para abrir el servidor ejecuta: python app.py")
else:
    from .app_instance import app
    from .controllers import ControladorPrincipal
    from .models import init_db

    ControladorPrincipal.registrar_contexto()
    try:
        init_db()
    except Exception as e:
        print(f"Advertencia: No se pudo conectar a la base de datos MySQL al importar models: {e}")

__all__ = ["app", "init_db"]

"""
Seguridad del lado del ADMINISTRADOR: contraseña, claves y firma del modelo.

Este archivo NO se incluye en el ejecutable del usuario: main.py no lo
importa en ningún punto de su cadena de importaciones (importa
interfaz_usuario -> deteccion -> verificacion, nunca este módulo).
La comprobación de la firma (sin ninguna clave privada) vive en
verificacion.py, que sí viaja con el programa del usuario.
"""
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from config import RUTA_MODELO, RUTA_FIRMA, RUTA_CLAVE_PUBLICA, RUTA_CLAVE_PRIVADA
from verificacion import firma_valida, modelo_firmado_valido  # reexportadas para admin.py


# ---------------- Administrador ----------------
def claves_existen():
    return os.path.exists(RUTA_CLAVE_PRIVADA) and os.path.exists(RUTA_CLAVE_PUBLICA)


def crear_claves(contrasena):
    """Primer uso: genera el par de claves; la privada queda cifrada con la contraseña."""
    clave = Ed25519PrivateKey.generate()
    with open(RUTA_CLAVE_PRIVADA, "wb") as f:
        f.write(clave.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(contrasena.encode("utf-8"))))
    with open(RUTA_CLAVE_PUBLICA, "wb") as f:
        f.write(clave.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo))
    return clave


def cargar_clave_privada(contrasena):
    """Devuelve la clave privada si la contraseña es correcta; si no, None."""
    try:
        with open(RUTA_CLAVE_PRIVADA, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=contrasena.encode("utf-8"))
    except (ValueError, TypeError):
        return None


# ---------------- Firma del modelo ----------------
def firmar_archivo_modelo(clave_privada):
    """Firma el modelo actual y guarda la firma junto a él."""
    with open(RUTA_MODELO, "rb") as f:
        datos = f.read()
    with open(RUTA_FIRMA, "wb") as f:
        f.write(clave_privada.sign(datos))
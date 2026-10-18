"""
Seguridad del proyecto.

1. Acceso de administrador: la clave privada (Ed25519) se guarda CIFRADA con la
   contraseña del administrador. Si la contraseña es incorrecta, no se puede
   descifrar la clave y no se puede entrenar ni firmar modelos.
2. Integridad del modelo: cada modelo entrenado se firma con esa clave privada.
   La app del usuario verifica la firma con la clave pública ANTES de cargar el
   modelo. Esto es importante porque los archivos .joblib (pickle) pueden ejecutar
   código arbitrario al cargarse: un modelo alterado en git sería un riesgo real.
"""
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.exceptions import InvalidSignature

from config import (RUTA_MODELO, RUTA_FIRMA, RUTA_CLAVE_PUBLICA, RUTA_CLAVE_PRIVADA)


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


def firma_valida(datos_modelo):
    """True solo si la firma existe y corresponde exactamente a estos bytes del modelo."""
    try:
        with open(RUTA_CLAVE_PUBLICA, "rb") as f:
            clave_publica = serialization.load_pem_public_key(f.read())
        with open(RUTA_FIRMA, "rb") as f:
            firma = f.read()
        clave_publica.verify(firma, datos_modelo)
        return True
    except (OSError, ValueError, InvalidSignature):
        return False


def modelo_firmado_valido():
    if not os.path.exists(RUTA_MODELO):
        return False
    with open(RUTA_MODELO, "rb") as f:
        return firma_valida(f.read())
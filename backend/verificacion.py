"""
Verificación de la firma del modelo.

Este módulo NO puede crear firmas ni contiene ninguna clave privada: solo
sabe comprobar una firma ya existente. La clave pública está incrustada en
el propio programa (clave_publica_embebida.py) en lugar de leerse de un
archivo .pem junto al ejecutable, para que no se pueda sustituir con solo
reemplazar un archivo: haría falta modificar el programa mismo y recompilarlo.
"""
import os
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from clave_publica_embebida import CLAVE_PUBLICA_PEM
from config import RUTA_MODELO, RUTA_FIRMA


def firma_valida(datos_modelo):
    """True solo si la firma en RUTA_FIRMA corresponde exactamente a estos bytes."""
    try:
        clave_publica = serialization.load_pem_public_key(CLAVE_PUBLICA_PEM)
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
"""
Herramienta de administrador: incrusta la clave pública actual
(clave_publica.pem) dentro del propio programa (clave_publica_embebida.py),
en vez de dejarla como un archivo que se pueda sustituir junto al ejecutable.

Ejecutar:
  - La primera vez, después de crear las claves con "python admin.py".
  - Cada vez que se rote o se vuelva a generar el par de claves.
Después de ejecutar esto, hay que volver a construir el .exe
(construir_exe.ps1) para que use la clave nueva.

Uso:
    python generar_clave_embebida.py
"""
import os

from config import RUTA_CLAVE_PUBLICA

DESTINO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clave_publica_embebida.py")


def main():
    if not os.path.exists(RUTA_CLAVE_PUBLICA):
        print(f"No se encontró {RUTA_CLAVE_PUBLICA}.")
        print("Ejecute primero 'python admin.py' para crear las claves.")
        return

    with open(RUTA_CLAVE_PUBLICA, "rb") as f:
        pem = f.read()

    contenido = (
        '"""Clave pública incrustada en el programa.\n'
        'Generado automáticamente con generar_clave_embebida.py. NO editar a mano.\n'
        'Contiene solo la clave PÚBLICA: sirve para comprobar firmas, nunca para crearlas."""\n\n'
        f"CLAVE_PUBLICA_PEM = {pem!r}\n"
    )
    with open(DESTINO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"Listo: {DESTINO} actualizado con la clave pública actual.")
    print("Vuelva a construir el .exe para que use esta clave.")


if __name__ == "__main__":
    main()
"""Punto de entrada para el USUARIO: solo detección de señas (sin entrenamiento).

Este archivo solo importa interfaz_usuario.py, que a su vez solo usa
deteccion.py y verificacion.py. El código de entrenamiento, grabación de
muestras y manejo de claves de administrador (interfaz.py,
aprendizaje_supervisado.py, seguridad.py, admin.py) nunca se importa desde
aquí, así que no viaja dentro del ejecutable del usuario.
"""
import os
import sys
import tkinter as tk

# En el .exe sin consola (--windowed) sys.stdout / sys.stderr valen None y
# algunas librerías intentan escribir en ellos. Se redirigen para evitarlo.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from interfaz_usuario import DetectorSenasApp


def main():
    root = tk.Tk()
    app = DetectorSenasApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
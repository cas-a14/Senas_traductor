"""Punto de entrada del ADMINISTRADOR: requiere contraseña. Detección + grabación + entrenamiento."""
import os
import tkinter as tk
from tkinter import simpledialog, messagebox

import seguridad
from config import MIN_LONGITUD_CONTRASENA, RUTA_MODELO
from interfaz import DetectorSenasApp

MAX_INTENTOS = 3


def autenticar(root):
    """Pide la contraseña (o la crea en el primer uso). Devuelve la clave privada o None."""
    if not seguridad.claves_existen():
        # Primer uso: crear contraseña y claves
        while True:
            p1 = simpledialog.askstring(
                "Configuración inicial",
                f"Cree la contraseña de administrador (mínimo {MIN_LONGITUD_CONTRASENA} caracteres):",
                show="*", parent=root)
            if p1 is None:
                return None
            if len(p1) < MIN_LONGITUD_CONTRASENA:
                messagebox.showwarning("Contraseña débil",
                                       f"Use al menos {MIN_LONGITUD_CONTRASENA} caracteres.")
                continue
            p2 = simpledialog.askstring("Configuración inicial", "Confirme la contraseña:",
                                        show="*", parent=root)
            if p2 is None:
                return None
            if p1 != p2:
                messagebox.showwarning("No coinciden", "Las contraseñas no coinciden.")
                continue
            break
        clave = seguridad.crear_claves(p1)
        messagebox.showinfo(
            "Claves creadas",
            "Se creó 'clave_privada_admin.pem' (cifrada con su contraseña).\n\n"
            "NO la suba a git y haga una copia de respaldo: sin ella no podrá firmar modelos.\n"
            "'clave_publica.pem' sí debe subirse a git.")
        return clave

    for _ in range(MAX_INTENTOS):
        p = simpledialog.askstring("Modo administrador", "Contraseña de administrador:",
                                   show="*", parent=root)
        if p is None:
            return None
        clave = seguridad.cargar_clave_privada(p)
        if clave is not None:
            return clave
        messagebox.showerror("Acceso denegado", "Contraseña incorrecta.")
    return None


def main():
    root = tk.Tk()
    root.withdraw()                      # oculta la ventana mientras se autentica

    clave = autenticar(root)
    if clave is None:
        root.destroy()
        return

    # Si hay un modelo sin firma válida (por ejemplo, el entrenado antes de este cambio),
    # el administrador decide si confía en él y lo firma.
    if os.path.exists(RUTA_MODELO) and not seguridad.modelo_firmado_valido():
        if messagebox.askyesno(
                "Modelo sin firma válida",
                "El modelo actual no tiene una firma válida.\n\n"
                "¿Confía en este archivo y desea firmarlo ahora?\n"
                "(Responda 'No' si no reconoce el archivo.)", parent=root):
            seguridad.firmar_archivo_modelo(clave)

    root.deiconify()
    app = DetectorSenasApp(root, modo_admin=True)
    app.clasificador.clave_privada = clave
    app.clasificador.cargar_modelo()     # recarga por si se acaba de firmar
    if app.clasificador.tiene_modelo():
        app.actualizar_estado("Modelo cargado correctamente (firma verificada)")
    root.mainloop()


if __name__ == "__main__":
    main()
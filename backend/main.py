"""Punto de entrada para el USUARIO: solo detección de señas (sin entrenamiento)."""
import tkinter as tk

from interfaz import DetectorSenasApp


def main():
    root = tk.Tk()
    app = DetectorSenasApp(root, modo_admin=False)
    root.mainloop()


if __name__ == "__main__":
    main()
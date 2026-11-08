"""
Interfaz gráfica del USUARIO: solo detección de señas (Tkinter + MediaPipe).

Este módulo es el único que importa main.py. No contiene ninguna lógica de
grabación de muestras, entrenamiento ni manejo de claves de administrador:
esa lógica vive en interfaz.py / aprendizaje_supervisado.py / seguridad.py,
que admin.py importa por separado y que el ejecutable del usuario no incluye.
"""
import cv2
import mediapipe as mp
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import queue
import time
import numpy as np

from deteccion import ClasificadorSenas
from dibujo import dibujar_caja_delimitadora


class DetectorSenasApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Detector de Lenguaje de Señas")
        self.root.geometry("1280x720")
        self.root.resizable(True, True)
        self.root.configure(bg="#292929")

        self.ejecutando = False
        self.letra_detectada = None
        self.frame_cola = queue.Queue(maxsize=2)
        self.letra_detectada_cola = queue.Queue(maxsize=2)
        self.hilo_video = None

        self.clasificador = ClasificadorSenas()

        self.mp_dibujo = mp.solutions.drawing_utils
        self.mp_estilos_dibujo = mp.solutions.drawing_styles
        self.mp_manos = mp.solutions.hands

        self.crear_interfaz()

        if not self.clasificador.tiene_modelo():
            if self.clasificador.error_modelo:
                self.actualizar_estado(self.clasificador.error_modelo)
            else:
                self.actualizar_estado("No se encontró el modelo entrenado (modelo_senas.joblib).")
        else:
            self.actualizar_estado("Modelo cargado correctamente")

    def crear_interfaz(self):
        panel_principal = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        panel_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.panel_video = ttk.Frame(panel_principal)
        panel_principal.add(self.panel_video, weight=3)

        self.canvas_video = tk.Canvas(self.panel_video, bg="black")
        self.canvas_video.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        panel_derecho = ttk.Frame(panel_principal)
        panel_principal.add(panel_derecho, weight=1)

        titulo_label = tk.Label(panel_derecho, text="Detector de\nLenguaje de Señas",
                              font=("Arial", 24, "bold"), bg="#292929", fg="white")
        titulo_label.pack(pady=20)

        panel_resultados = ttk.LabelFrame(panel_derecho, text="Letra Detectada")
        panel_resultados.pack(fill=tk.BOTH, padx=10, pady=10)

        self.letra_label = tk.Label(panel_resultados, text="?",
                                  font=("Arial", 120, "bold"), fg="red", bg="#f0f0f0")
        self.letra_label.pack(pady=20)

        panel_controles = ttk.LabelFrame(panel_derecho, text="Controles")
        panel_controles.pack(fill=tk.X, padx=10, pady=10)

        estilo_boton = ttk.Style()
        estilo_boton.configure("Accion.TButton", font=("Arial", 14))

        self.btn_iniciar = ttk.Button(panel_controles, text="Iniciar", style="Accion.TButton",
                                    command=self.iniciar_deteccion)
        self.btn_iniciar.pack(fill=tk.X, padx=20, pady=10)

        self.btn_detener = ttk.Button(panel_controles, text="Detener", style="Accion.TButton",
                                     command=self.detener_deteccion, state=tk.DISABLED)
        self.btn_detener.pack(fill=tk.X, padx=20, pady=10)

        panel_info = ttk.LabelFrame(panel_derecho, text="Información")
        panel_info.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        info_texto = """
        Instrucciones:

        1. Presione "Iniciar" para comenzar la detección.
        2. Muestre su mano frente a la cámara.
        3. Forme letras del lenguaje de señas.
        4. La letra detectada aparecerá en el panel derecho.
        5. Presione "Detener" para finalizar.

        Letras implementadas: A-Z
        """

        info_label = tk.Label(panel_info, text=info_texto, justify=tk.LEFT,
                            font=("Arial", 10), bg="#f0f0f0")
        info_label.pack(padx=10, pady=10, fill=tk.BOTH)

        self.barra_estado = tk.Label(self.root, text="Listo", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.barra_estado.pack(side=tk.BOTTOM, fill=tk.X)

    def actualizar_estado(self, mensaje):
        if self.root and getattr(self, "barra_estado", None):
            self.barra_estado.config(text=mensaje)
            self.root.update_idletasks()

    def iniciar_deteccion(self):
        if not self.ejecutando:
            self.ejecutando = True
            self.btn_iniciar.config(state=tk.DISABLED)
            self.btn_detener.config(state=tk.NORMAL)
            self.actualizar_estado("Iniciando la cámara...")

            self.hilo_video = threading.Thread(target=self.procesar_video)
            self.hilo_video.daemon = True
            self.hilo_video.start()

            self.actualizar_interfaz()

    def detener_deteccion(self):
        if self.ejecutando:
            self.ejecutando = False
            self.btn_iniciar.config(state=tk.NORMAL)
            self.btn_detener.config(state=tk.DISABLED)
            self.actualizar_estado("Detenido")

            tiempo_espera = 0
            while self.hilo_video.is_alive() and tiempo_espera < 10:
                time.sleep(0.1)
                tiempo_espera += 1

            self.letra_label.config(text="?")

    def procesar_video(self):
        camara = cv2.VideoCapture(0)
        camara.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not camara.isOpened():
            self.actualizar_estado("No se pudo abrir la cámara")
            camara.release()
            self.ejecutando = False
            return

        self.actualizar_estado("Cámara iniciada. Detectando manos...")

        try:
            with self.mp_manos.Hands(
                model_complexity=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.7,
                max_num_hands=1
            ) as manos:

                while self.ejecutando and camara.isOpened():
                    exito, imagen = camara.read()

                    if not exito or imagen is None:
                        continue

                    imagen = cv2.flip(imagen, 1)

                    imagen_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
                    imagen_rgb = np.ascontiguousarray(imagen_rgb)
                    imagen_rgb.flags.writeable = False

                    resultados = manos.process(imagen_rgb)

                    letra_actual = None

                    if resultados.multi_hand_landmarks:
                        for puntos_mano in resultados.multi_hand_landmarks:
                            self.mp_dibujo.draw_landmarks(
                                imagen,
                                puntos_mano,
                                self.mp_manos.HAND_CONNECTIONS,
                                self.mp_estilos_dibujo.get_default_hand_landmarks_style(),
                                self.mp_estilos_dibujo.get_default_hand_connections_style()
                            )

                            letra_actual = self.clasificador.predecir(puntos_mano)

                            dibujar_caja_delimitadora(imagen, puntos_mano, letra_actual)

                    if not self.frame_cola.full():
                        frame_redimensionado = cv2.resize(imagen, (960, 720))
                        self.frame_cola.put(frame_redimensionado)

                    if letra_actual and not self.letra_detectada_cola.full():
                        self.letra_detectada_cola.put(letra_actual)

                    if cv2.waitKey(5) & 0xFF == 27:
                        break

        except Exception as error:
            print("Error al procesar el video:", error)
            self.actualizar_estado("Error al procesar la cámara")

        finally:
            camara.release()
            self.ejecutando = False
            self.actualizar_estado("Cámara detenida")

    def actualizar_interfaz(self):
        if not self.ejecutando:
            return

        if not self.frame_cola.empty():
            frame = self.frame_cola.get()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)

            self.canvas_video.config(width=img.width, height=img.height)
            self.canvas_video.create_image(0, 0, anchor=tk.NW, image=imgtk)
            self.canvas_video.imagen = imgtk

        if not self.letra_detectada_cola.empty():
            nueva_letra = self.letra_detectada_cola.get()
            if nueva_letra != self.letra_detectada:
                self.letra_detectada = nueva_letra
                self.letra_label.config(text=nueva_letra)

        self.root.after(15, self.actualizar_interfaz)
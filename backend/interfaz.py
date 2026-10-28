"""Interfaz gráfica (Tkinter) y procesamiento de video con MediaPipe."""
import cv2
import mediapipe as mp
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import queue
import time
import numpy as np

from config import RUTA_DATASET
from aprendizaje_supervisado import ClasificadorSenas, extraer_caracteristicas
from dibujo import dibujar_caja_delimitadora


class DetectorSenasApp:
    def __init__(self, root, modo_admin=False):
        self.root = root
        self.modo_admin = modo_admin
        titulo_ventana = "Detector de Lenguaje de Señas"
        if modo_admin:
            titulo_ventana += " - Modo administrador"
        self.root.title(titulo_ventana)
        self.root.geometry("1280x720")
        self.root.resizable(True, True)
        self.root.configure(bg="#292929")

        # Variables de control
        self.ejecutando = False
        self.letra_detectada = None
        self.frame_cola = queue.Queue(maxsize=2)
        self.letra_detectada_cola = queue.Queue(maxsize=2)
        self.hilo_video = None

        # Modelo supervisado y variables de grabación
        self.clasificador = ClasificadorSenas()
        self.grabando = False
        self.letra_a_grabar = "A"
        self.muestras_nuevas = []          # lista de (letra, vector de 63 valores)
        self.ultimo_tiempo_muestra = 0.0
        self.entrenando = False

        # Configuración de MediaPipe
        self.mp_dibujo = mp.solutions.drawing_utils
        self.mp_estilos_dibujo = mp.solutions.drawing_styles
        self.mp_manos = mp.solutions.hands

        # Crear estructura de la interfaz
        self.crear_interfaz()

        if not self.clasificador.tiene_modelo():
            if self.modo_admin:
                self.actualizar_estado("Sin modelo entrenado. Grabe muestras de cada letra "
                                       "y pulse 'Entrenar y evaluar modelo'.")
            elif self.clasificador.error_modelo:
                self.actualizar_estado(self.clasificador.error_modelo)
            else:
                self.actualizar_estado("No se encontró el modelo entrenado (modelo_senas.joblib).")
        else:
            self.actualizar_estado("Modelo cargado correctamente")

    def crear_interfaz(self):
        # Panel principal dividido en dos secciones
        panel_principal = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        panel_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Panel izquierdo - Video
        self.panel_video = ttk.Frame(panel_principal)
        panel_principal.add(self.panel_video, weight=3)

        # Panel de video
        self.canvas_video = tk.Canvas(self.panel_video, bg="black")
        self.canvas_video.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Panel derecho - Controles y resultados
        panel_derecho = ttk.Frame(panel_principal)
        panel_principal.add(panel_derecho, weight=1)

        # Título
        titulo_label = tk.Label(panel_derecho, text="Detector de\nLenguaje de Señas",
                              font=("Arial", 24, "bold"), bg="#292929", fg="white")
        titulo_label.pack(pady=20)

        # Panel de resultados
        panel_resultados = ttk.LabelFrame(panel_derecho, text="Letra Detectada")
        panel_resultados.pack(fill=tk.BOTH, padx=10, pady=10)

        self.letra_label = tk.Label(panel_resultados, text="?",
                                  font=("Arial", 120, "bold"), fg="red", bg="#f0f0f0")
        self.letra_label.pack(pady=20)

        # Panel de controles
        panel_controles = ttk.LabelFrame(panel_derecho, text="Controles")
        panel_controles.pack(fill=tk.X, padx=10, pady=10)

        # Botones de control
        estilo_boton = ttk.Style()
        estilo_boton.configure("Accion.TButton", font=("Arial", 14))

        self.btn_iniciar = ttk.Button(panel_controles, text="Iniciar", style="Accion.TButton",
                                    command=self.iniciar_deteccion)
        self.btn_iniciar.pack(fill=tk.X, padx=20, pady=10)

        self.btn_detener = ttk.Button(panel_controles, text="Detener", style="Accion.TButton",
                                     command=self.detener_deteccion, state=tk.DISABLED)
        self.btn_detener.pack(fill=tk.X, padx=20, pady=10)

        # Panel de entrenamiento: solo visible para el administrador
        if self.modo_admin:
            self.crear_panel_entrenamiento(panel_derecho)

        # Panel de información
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

        # Barra de estado
        self.barra_estado = tk.Label(self.root, text="Listo", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.barra_estado.pack(side=tk.BOTTOM, fill=tk.X)

    def crear_panel_entrenamiento(self, panel_derecho):
        """Panel de grabación de muestras y entrenamiento (solo modo administrador)"""
        # Panel de entrenamiento supervisado
        panel_entrenamiento = ttk.LabelFrame(panel_derecho, text="Entrenamiento (aprendizaje supervisado)")
        panel_entrenamiento.pack(fill=tk.X, padx=10, pady=10)

        fila_letra = ttk.Frame(panel_entrenamiento)
        fila_letra.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(fila_letra, text="Etiqueta (letra):").pack(side=tk.LEFT)
        self.combo_letra = ttk.Combobox(
            fila_letra, values=[chr(c) for c in range(ord("A"), ord("Z") + 1)],
            width=5, state="readonly")
        self.combo_letra.set("A")
        self.combo_letra.pack(side=tk.LEFT, padx=10)

        self.btn_grabar = ttk.Button(panel_entrenamiento, text="Grabar muestras",
                                     command=self.alternar_grabacion)
        self.btn_grabar.pack(fill=tk.X, padx=20, pady=5)

        self.btn_entrenar = ttk.Button(panel_entrenamiento, text="Entrenar y evaluar modelo",
                                       command=self.entrenar_modelo)
        self.btn_entrenar.pack(fill=tk.X, padx=20, pady=5)

        self.lbl_muestras = tk.Label(panel_entrenamiento, text="Muestras grabadas: 0",
                                     font=("Arial", 9))
        self.lbl_muestras.pack(pady=5)

    def actualizar_estado(self, mensaje):
        """Actualiza el mensaje en la barra de estado"""
        if self.root and getattr(self, "barra_estado", None):
            self.barra_estado.config(text=mensaje)
            self.root.update_idletasks()

    # ------------------------------------------------------------------
    # Grabación de muestras y entrenamiento
    # ------------------------------------------------------------------
    def alternar_grabacion(self):
        """Activa/desactiva la captura de muestras etiquetadas con la letra elegida"""
        if not self.grabando:
            if not self.ejecutando:
                messagebox.showinfo("Cámara apagada",
                                    'Presione "Iniciar" primero para poder capturar muestras.')
                return
            self.letra_a_grabar = self.combo_letra.get()
            self.muestras_nuevas = []
            self.grabando = True
            self.btn_grabar.config(text="Detener grabación y guardar")
            self.combo_letra.config(state=tk.DISABLED)
            self.actualizar_estado(f"Grabando muestras de la letra {self.letra_a_grabar}. "
                                   "Mueva ligeramente la mano para variar las muestras.")
            self.actualizar_contador_muestras()
        else:
            self.grabando = False
            self.guardar_muestras()
            self.btn_grabar.config(text="Grabar muestras")
            self.combo_letra.config(state="readonly")

    def actualizar_contador_muestras(self):
        if self.grabando:
            self.lbl_muestras.config(
                text=f"Grabando '{self.letra_a_grabar}': {len(self.muestras_nuevas)} muestras")
            self.root.after(200, self.actualizar_contador_muestras)

    def guardar_muestras(self):
        """Guarda en el CSV las muestras capturadas"""
        muestras = list(self.muestras_nuevas)
        self.muestras_nuevas = []
        if not muestras:
            self.lbl_muestras.config(text="Muestras grabadas: 0")
            self.actualizar_estado("No se grabó ninguna muestra (¿se vio la mano?)")
            return

        self.clasificador.guardar_muestras(muestras)
        self.lbl_muestras.config(text=f"Guardadas {len(muestras)} muestras de '{muestras[0][0]}'")
        self.actualizar_estado(f"{len(muestras)} muestras guardadas en {RUTA_DATASET}")

    def entrenar_modelo(self):
        """Lanza el entrenamiento en un hilo para no congelar la interfaz"""
        if self.entrenando:
            return
        if self.grabando:
            messagebox.showinfo("Grabación activa", "Detenga la grabación antes de entrenar.")
            return
        self.entrenando = True
        self.btn_entrenar.config(state=tk.DISABLED)
        self.actualizar_estado("Entrenando modelo...")
        threading.Thread(target=self._entrenar, daemon=True).start()

    def _entrenar(self):
        mensaje = self.clasificador.entrenar()

        def terminar():
            self.entrenando = False
            self.btn_entrenar.config(state=tk.NORMAL)
            self.actualizar_estado("Entrenamiento finalizado")
            messagebox.showinfo("Entrenamiento", mensaje)
        self.root.after(0, terminar)

    # ------------------------------------------------------------------
    # Control de la detección
    # ------------------------------------------------------------------
    def iniciar_deteccion(self):
        """Inicia el proceso de detección de señas"""
        if not self.ejecutando:
            self.ejecutando = True
            self.btn_iniciar.config(state=tk.DISABLED)
            self.btn_detener.config(state=tk.NORMAL)
            self.actualizar_estado("Iniciando la cámara...")

            # Iniciar el hilo de procesamiento de video
            self.hilo_video = threading.Thread(target=self.procesar_video)
            self.hilo_video.daemon = True
            self.hilo_video.start()

            # Iniciar actualización de la interfaz
            self.actualizar_interfaz()

    def detener_deteccion(self):
        """Detiene el proceso de detección de señas"""
        if self.ejecutando:
            # Si se estaba grabando, se guardan las muestras antes de parar
            if self.grabando:
                self.alternar_grabacion()

            self.ejecutando = False
            self.btn_iniciar.config(state=tk.NORMAL)
            self.btn_detener.config(state=tk.DISABLED)
            self.actualizar_estado("Detenido")

            # Limpiar la visualización
            tiempo_espera = 0
            while self.hilo_video.is_alive() and tiempo_espera < 10:
                time.sleep(0.1)
                tiempo_espera += 1

            # Restablecer la letra detectada
            self.letra_label.config(text="?")

    def procesar_video(self):
        """Procesa el video de la cámara y detecta señas"""

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

                    # Preparar imagen para MediaPipe
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

                            # Captura de muestras etiquetadas (~10 por segundo)
                            if self.grabando and time.time() - self.ultimo_tiempo_muestra > 0.1:
                                self.muestras_nuevas.append(
                                    (self.letra_a_grabar, extraer_caracteristicas(puntos_mano)))
                                self.ultimo_tiempo_muestra = time.time()

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
        """Actualiza la interfaz con los frames y resultados de detección"""
        if not self.ejecutando:
            return

        # Actualizar frame de video
        if not self.frame_cola.empty():
            frame = self.frame_cola.get()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)

            self.canvas_video.config(width=img.width, height=img.height)
            self.canvas_video.create_image(0, 0, anchor=tk.NW, image=imgtk)
            self.canvas_video.imagen = imgtk

        # Actualizar letra detectada
        if not self.letra_detectada_cola.empty():
            nueva_letra = self.letra_detectada_cola.get()
            if nueva_letra != self.letra_detectada:
                self.letra_detectada = nueva_letra
                self.letra_label.config(text=nueva_letra)

        # Programar próxima actualización
        self.root.after(15, self.actualizar_interfaz)
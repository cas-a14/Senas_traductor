"""
Núcleo de detección: extracción de características y carga/predicción del
modelo.

Este es el ÚNICO módulo de "aprendizaje" que main.py necesita. No contiene
nada sobre el dataset, el entrenamiento ni las claves de administrador, para
que esa lógica no viaje dentro del ejecutable del usuario.
"""
import io
import os
import numpy as np
import joblib

import verificacion
from config import RUTA_MODELO, UMBRAL_CONFIANZA


def extraer_caracteristicas(puntos_mano):
    """
    Convierte los 21 landmarks de MediaPipe en un vector de 63 valores (x, y, z),
    independiente de la posición y del tamaño de la mano en la imagen:
      1. Se resta la muñeca (landmark 0) para centrar la mano.
      2. Se divide entre la mayor distancia (x, y) a la muñeca para normalizar la escala.
    """
    pts = np.array([[p.x, p.y, p.z] for p in puntos_mano.landmark], dtype=np.float32)
    pts -= pts[0]
    escala = np.linalg.norm(pts[:, :2], axis=1).max()
    if escala < 1e-6:
        escala = 1.0
    pts /= escala
    return pts.flatten()


class ClasificadorSenas:
    """Carga el modelo firmado y predice la letra. No entrena ni guarda datos."""

    def __init__(self):
        self.modelo = None
        self.error_modelo = None
        self.cargar_modelo()

    def cargar_modelo(self):
        """Carga el modelo SOLO si su firma digital es válida (clave embebida)."""
        self.modelo = None
        self.error_modelo = None
        if not os.path.exists(RUTA_MODELO):
            return
        try:
            with open(RUTA_MODELO, "rb") as f:
                datos = f.read()
            if not verificacion.firma_valida(datos):
                self.error_modelo = ("El modelo no tiene una firma válida y no se cargó. "
                                     "Descargue de nuevo la versión oficial del programa.")
                return
            # Se carga desde los mismos bytes verificados (evita que cambien tras verificar)
            self.modelo = joblib.load(io.BytesIO(datos))
        except Exception as error:
            print("No se pudo cargar el modelo:", error)
            self.error_modelo = "No se pudo cargar el modelo."
            self.modelo = None

    def tiene_modelo(self):
        return self.modelo is not None

    def predecir(self, puntos_mano):
        """Predice la letra, o "?" si no hay modelo o la confianza es baja."""
        if self.modelo is None:
            return "?"
        try:
            caracteristicas = extraer_caracteristicas(puntos_mano).reshape(1, -1)
            probabilidades = self.modelo.predict_proba(caracteristicas)[0]
            indice = int(np.argmax(probabilidades))
            if probabilidades[indice] >= UMBRAL_CONFIANZA:
                return str(self.modelo.classes_[indice])
        except Exception as error:
            print("Error al predecir:", error)
        return "?"
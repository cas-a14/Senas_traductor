"""
Aprendizaje supervisado: extracción de características, manejo del dataset
etiquetado, entrenamiento, evaluación y predicción (RandomForest).
"""
import io
import os
import csv
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

import seguridad
from config import (RUTA_DATASET, RUTA_MODELO, UMBRAL_CONFIANZA,
                    MIN_MUESTRAS_POR_LETRA, NUM_CARACTERISTICAS)


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
    """Gestiona el dataset, el entrenamiento y las predicciones del modelo."""

    def __init__(self):
        self.modelo = None
        self.error_modelo = None      # motivo por el que no se cargó el modelo (si aplica)
        self.clave_privada = None     # solo la asigna el modo administrador tras autenticarse
        self.cargar_modelo()

    # ---------------- Modelo ----------------
    def cargar_modelo(self):
        """Carga el modelo SOLO si su firma digital es válida"""
        self.modelo = None
        self.error_modelo = None
        if not os.path.exists(RUTA_MODELO):
            return
        try:
            with open(RUTA_MODELO, "rb") as f:
                datos = f.read()
            if not seguridad.firma_valida(datos):
                self.error_modelo = ("El modelo no tiene una firma válida y no se cargó. "
                                     "Descargue de nuevo el modelo oficial.")
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
        """
        Predice la letra a partir de los landmarks de la mano. Devuelve "?" si
        no hay modelo o si la confianza es menor al umbral.
        """
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

    # ---------------- Dataset ----------------
    def guardar_muestras(self, muestras):
        """Agrega las muestras [(letra, vector), ...] al CSV (letra + 63 características)"""
        nuevo_archivo = not os.path.exists(RUTA_DATASET)
        with open(RUTA_DATASET, "a", newline="", encoding="utf-8") as f:
            escritor = csv.writer(f)
            if nuevo_archivo:
                escritor.writerow(["letra"] + [f"f{i}" for i in range(NUM_CARACTERISTICAS)])
            for letra, vector in muestras:
                escritor.writerow([letra] + [f"{v:.6f}" for v in vector])

    def cargar_dataset(self):
        """Lee el CSV y devuelve X (características) e y (etiquetas)"""
        if not os.path.exists(RUTA_DATASET):
            return None, None
        etiquetas, vectores = [], []
        with open(RUTA_DATASET, newline="", encoding="utf-8") as f:
            lector = csv.reader(f)
            next(lector, None)  # saltar encabezado
            for fila in lector:
                if len(fila) != NUM_CARACTERISTICAS + 1:
                    continue
                etiquetas.append(fila[0])
                vectores.append([float(v) for v in fila[1:]])
        if not etiquetas:
            return None, None
        return np.array(vectores, dtype=np.float32), np.array(etiquetas)

    # ---------------- Entrenamiento ----------------
    def entrenar(self):
        """
        Entrena RandomForest, evalúa con datos de prueba (20 %) y guarda el modelo
        final entrenado con todos los datos. Devuelve el mensaje para el usuario.
        """
        try:
            X, y = self.cargar_dataset()
            if X is None:
                return (f"No existe el archivo '{RUTA_DATASET}' o está vacío.\n\n"
                        "Use 'Iniciar' y luego 'Grabar muestras' para capturar datos "
                        "etiquetados de cada letra.")

            letras, cuentas = np.unique(y, return_counts=True)
            if len(letras) < 2:
                return "Se necesitan muestras de al menos 2 letras distintas."
            if cuentas.min() < MIN_MUESTRAS_POR_LETRA:
                escasas = ", ".join(f"{l}({c})" for l, c in zip(letras, cuentas)
                                    if c < MIN_MUESTRAS_POR_LETRA)
                return (f"Hay letras con menos de {MIN_MUESTRAS_POR_LETRA} muestras: "
                        f"{escasas}.\nGrabe más muestras (se recomiendan 100 o más por letra).")

            # División entrenamiento / prueba (80 % / 20 %), estratificada
            X_ent, X_prueba, y_ent, y_prueba = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y)

            modelo = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
            modelo.fit(X_ent, y_ent)

            pred = modelo.predict(X_prueba)
            exactitud = accuracy_score(y_prueba, pred)
            reporte = classification_report(y_prueba, pred, zero_division=0)
            print("\n===== Evaluación con datos de prueba =====")
            print(f"Exactitud: {exactitud:.3f}\n{reporte}")

            # Modelo final: se reentrena con todos los datos disponibles
            modelo_final = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
            modelo_final.fit(X, y)
            joblib.dump(modelo_final, RUTA_MODELO)
            self.modelo = modelo_final

            # Firma digital del nuevo modelo (solo posible con la clave del administrador)
            nota_firma = "AVISO: el modelo NO se firmó (sin sesión de administrador)."
            if self.clave_privada is not None:
                seguridad.firmar_archivo_modelo(self.clave_privada)
                nota_firma = "Modelo firmado digitalmente."

            return (f"Letras: {len(letras)} | Muestras totales: {len(y)}\n"
                    f"Entrenamiento: {len(y_ent)} | Prueba: {len(y_prueba)}\n\n"
                    f"Exactitud en datos de prueba: {exactitud * 100:.1f} %\n\n"
                    f"Modelo guardado en '{RUTA_MODELO}'. {nota_firma}\n"
                    "El reporte completo por letra está en la consola.")
        except Exception as error:
            return f"Error durante el entrenamiento:\n{error}"